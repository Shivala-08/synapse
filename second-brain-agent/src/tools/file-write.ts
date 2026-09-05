import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { mkdir, writeFile } from 'fs/promises';
import { dirname } from 'path';
import { VAULT, assertInsideVault } from '../vault-path.js';

export const fileWriteTool = tool({
  name: 'file_write',
  description: 'Write or create a file inside the Second Brain vault. Requires user approval.',
  requireApproval: true,
  inputSchema: z.object({
    path: z.string().describe('Absolute path inside the Second Brain vault'),
    content: z.string().describe('Complete file contents')
  }),
  execute: async ({ path, content }) => {
    try {
      const target = assertInsideVault(path);

      await mkdir(dirname(target), { recursive: true });
      await writeFile(target, content, 'utf-8');

      return {
        written: true,
        path: target
      };
    } catch (err: any) {
      return {
        error: err.message
      };
    }
  }
});
