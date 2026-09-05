import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import type { AgentConfig } from './config.js';

export function buildSystemPrompt(config: AgentConfig): string {
  let prompt = config.systemPrompt
    .replace('{vaultDir}', config.vaultDir);

  const contextFiles = ['CLAUDE.md', 'AGENTS.md', '.agent-context.md'];

  for (const filename of contextFiles) {
    const filePath = resolve(config.vaultDir, filename);

    if (existsSync(filePath)) {
      const content = readFileSync(filePath, 'utf-8');
      prompt += `\n\n## ${filename}\n\n${content}`;
    }
  }

  return prompt;
}
