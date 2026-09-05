import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { execFile } from 'child_process';
import { VAULT } from '../vault-path.js';

export const grepTool = tool({
  name: 'grep',
  description: 'Search the Second Brain vault for matching content.',
  inputSchema: z.object({
    pattern: z.string(),
    path: z.string().optional(),
    glob: z.string().optional(),
    ignoreCase: z.boolean().optional()
  }),
  execute: async ({ pattern, path, glob: fileGlob, ignoreCase }) => {
    const args = [
      '--line-number',
      '--with-filename',
      '--max-count=100'
    ];

    if (ignoreCase) args.push('--ignore-case');
    if (fileGlob) args.push('--glob', fileGlob);

    args.push(pattern, path ?? VAULT);

    return new Promise((resolve) => {
      execFile('rg', args, { maxBuffer: 256 * 1024 }, (error, stdout, stderr) => {
        if (error && error.code !== 1) {
          resolve({ error: stderr || error.message });
          return;
        }

        resolve(stdout || 'No matches found.');
      });
    });
  }
});
