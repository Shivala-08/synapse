import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { readFile } from 'fs/promises';
import { extname } from 'path';

const DEFAULT_LINE_LIMIT = 2000;
const MAX_LINE_CHARS = 2000;

export const fileReadTool = tool({
  name: 'file_read',
  description: 'Read a file from the Second Brain vault. Supports pagination.',
  inputSchema: z.object({
    path: z.string().describe('Absolute path to the file'),
    offset: z.number().optional().describe('Start line, 1-indexed'),
    limit: z.number().optional().describe('Maximum lines to return')
  }),
  execute: async ({ path, offset, limit }) => {
    try {
      const content = await readFile(path, 'utf-8');
      const lines = content.split('\n');
      const start = offset ? offset - 1 : 0;
      const end = Math.min(
        start + (limit ?? DEFAULT_LINE_LIMIT),
        lines.length
      );

      let longLines = 0;

      const slice = lines.slice(start, end).map((line) => {
        if (line.length <= MAX_LINE_CHARS) return line;
        longLines++;
        return line.slice(0, MAX_LINE_CHARS) +
          `… [line truncated, ${line.length - MAX_LINE_CHARS} chars dropped]`;
      });

      const tailTruncated = end < lines.length;
      const truncated = tailTruncated || longLines > 0;

      const result: Record<string, unknown> = {
        content: slice.join('\n'),
        totalLines: lines.length
      };

      if (truncated) {
        result.truncated = true;

        const hints: string[] = [
          `Showing lines ${start + 1}-${end} of ${lines.length}.`
        ];

        if (tailTruncated) {
          result.nextOffset = end + 1;
          hints.push(`Use offset=${end + 1} to continue.`);
        }

        if (longLines > 0) {
          hints.push(
            `${longLines} line(s) exceeded ${MAX_LINE_CHARS} characters.`
          );
        }

        result.hint = hints.join(' ');
      }

      return result;
    } catch (err: any) {
      if (err.code === 'ENOENT') {
        return { error: `File not found: ${path}` };
      }

      if (err.code === 'EACCES') {
        return { error: `Permission denied: ${path}` };
      }

      return { error: err.message };
    }
  }
});
