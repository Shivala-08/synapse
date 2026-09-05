import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { glob } from 'glob';
import { VAULT } from '../vault-path.js';

export const globTool = tool({
  name: 'glob',
  description: 'Find files in the Second Brain vault using glob patterns.',
  inputSchema: z.object({
    pattern: z.string(),
    path: z.string().optional()
  }),
  execute: async ({ pattern, path }) => {
    try {
      return await glob(pattern, {
        cwd: path ?? VAULT,
        ignore: ['**/.git/**', '**/.sessions/**'],
        nodir: true
      });
    } catch (err: any) {
      return { error: err.message };
    }
  }
});
