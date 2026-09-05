import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { readFile, writeFile } from 'fs/promises';
import { VAULT, assertInsideVault } from '../vault-path.js';

export const fileEditTool = tool({
  name: 'file_edit',
  description: 'Apply exact search-and-replace edits to a file inside the Second Brain vault. Requires approval.',
  requireApproval: true,
  inputSchema: z.object({
    path: z.string().describe('Absolute path inside the vault'),
    edits: z.array(
      z.object({
        old_text: z.string(),
        new_text: z.string()
      })
    )
  }),
  execute: async ({ path, edits }) => {
    try {
      const target = assertInsideVault(path);
      let content = await readFile(target, 'utf-8');
      const original = content;

      for (const edit of edits) {
        const occurrences = content.split(edit.old_text).length - 1;

        if (occurrences === 0) {
          return {
            error: `Text not found in ${target}`
          };
        }

        if (occurrences !== 1) {
          return {
            error: `Edit is ambiguous: found ${occurrences} occurrences in ${target}`
          };
        }

        content = content.replace(edit.old_text, edit.new_text);
      }

      await writeFile(target, content, 'utf-8');

      return {
        edited: true,
        path: target,
        changed: original !== content
      };
    } catch (err: any) {
      return {
        error: err.message
      };
    }
  }
});
