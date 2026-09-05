import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { readdir } from 'fs/promises';
import { VAULT } from '../vault-path.js';

export const listDirTool = tool({
  name: 'list_dir',
  description: 'List files and directories in the Second Brain vault.',
  inputSchema: z.object({
    path: z.string().optional()
  }),
  execute: async ({ path }) => {
    try {
      const entries = await readdir(path ?? VAULT, {
        withFileTypes: true
      });

      return entries
        .sort((a, b) => a.name.localeCompare(b.name))
        .slice(0, 500)
        .map((entry) => entry.isDirectory() ? `${entry.name}/` : entry.name);
    } catch (err: any) {
      return { error: err.message };
    }
  }
});
