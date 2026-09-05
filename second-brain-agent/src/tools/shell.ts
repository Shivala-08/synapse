import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { execFile } from 'child_process';
import { VAULT } from '../vault-path.js';

export const shellTool = tool({
  name: 'shell',
  description: 'Run a shell command from the Second Brain vault. Dangerous commands require approval.',
  requireApproval: ({ command }: { command: string }) =>
    /\brm\b|\bsudo\b|\bchmod\b|\bchown\b|\bdd\b|\bmkfs\b/.test(command),
  inputSchema: z.object({
    command: z.string(),
    timeout: z.number().optional()
  }),
  execute: async ({ command, timeout }) => {
    return new Promise((resolve) => {
      execFile(
        process.env.SHELL || '/bin/bash',
        ['-lc', command],
        {
          cwd: VAULT,
          timeout: (timeout ?? 120) * 1000,
          maxBuffer: 256 * 1024
        },
        (error, stdout, stderr) => {
          const output = `${stdout}${stderr}`;

          resolve({
            output: output.slice(-256 * 1024),
            exitCode: error ? (error.code ?? 1) : 0,
            timedOut: Boolean((error as any)?.killed)
          });
        }
      );
    });
  }
});
