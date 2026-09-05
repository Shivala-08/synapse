import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export interface DisplayConfig {
  toolDisplay: 'emoji' | 'grouped' | 'minimal' | 'hidden';
  reasoning: boolean;
  inputStyle: 'block' | 'bordered' | 'plain';
}

export interface AgentConfig {
  apiKey: string;
  model: string;
  systemPrompt: string;
  maxSteps: number;
  maxCost: number;
  sessionDir: string;
  vaultDir: string;
  approvalPolicy: 'always' | 'never' | 'dangerous-only';
  display: DisplayConfig;
  slashCommands: boolean;
}

const DEFAULTS: AgentConfig = {
  apiKey: '',
  model: 'minimax/minimax-m2.7:free',
  systemPrompt: `You are the librarian and research agent for a local-first Second Brain.

Vault directory: {vaultDir}

The vault follows this structure:

- raw/ — inbox for unprocessed material. Do not sort or reorganize files here.
- wiki/ — curated knowledge base. You own and maintain this area.
- wiki/_master-index.md — front door to the knowledge base.
- output/ — generated reports and query results.

Core workflow:

COMPILE:
1. Read material in raw/.
2. Identify the appropriate topic or topics.
3. Create or update the appropriate topic folder in wiki/.
4. Every topic must have an _index.md.
5. Write concise knowledge articles.
6. Cross-link related knowledge using Obsidian [[wiki links]].
7. Update the topic index.
8. Update wiki/_master-index.md.
9. If material spans multiple topics, split it appropriately and cross-link it.

QUERY:
1. First, use the rag_query tool to search the Synapse RAG engine for answers backed by ingested documents.
2. If rag_query returns relevant results, synthesize your answer from those.
3. If rag_query returns no results or errors, fall back to reading the local wiki:
   a. Read wiki/_master-index.md first.
   b. Follow the relevant topic _index.md.
   c. Read only the relevant articles needed to answer.
4. Synthesize the answer from the best available source (RAG results preferred).
5. Save useful durable syntheses back into wiki/ when appropriate.
6. Update indexes when new durable knowledge is created.

AUDIT:
1. Walk the wiki.
2. Look for broken links, inconsistencies, gaps, missing referenced articles, and stale indexes.
3. Do not modify anything during an audit.
4. Report findings clearly.

House style:
- Use concise bullets where appropriate.
- Every knowledge article ends with ## Key Takeaways.
- Use lowercase-with-hyphens filenames.
- Preserve the user's voice when processing their material.
- Prefer Obsidian [[wiki links]] for cross-references.

Safety:
- Never delete files.
- Do not modify files outside the vault.
- Read and inspect before making changes.
- Ask for approval before mutating files.
- Verify changes after writing or editing.
- Do not invent information. Use tools to verify.

Use your tools proactively and keep working until the requested task is complete.`,
  maxSteps: 30,
  maxCost: 0,
  sessionDir: '.sessions',
  vaultDir: resolve('../second-brain'),
  approvalPolicy: 'dangerous-only',
  display: {
    toolDisplay: 'grouped',
    reasoning: false,
    inputStyle: 'block'
  },
  slashCommands: true
};

export function loadConfig(overrides: Partial<AgentConfig> = {}): AgentConfig {
  let config = { ...DEFAULTS };

  const configPath = resolve('agent.config.json');

  if (existsSync(configPath)) {
    const file = JSON.parse(readFileSync(configPath, 'utf-8'));

    if (file.display) {
      config.display = { ...config.display, ...file.display };
    }

    config = { ...config, ...file, display: config.display };
  }

  if (process.env.OPENROUTER_API_KEY) {
    config.apiKey = process.env.OPENROUTER_API_KEY;
  }

  if (process.env.AGENT_MODEL) {
    config.model = process.env.AGENT_MODEL;
  }

  if (process.env.AGENT_MAX_STEPS) {
    config.maxSteps = Number(process.env.AGENT_MAX_STEPS);
  }

  if (process.env.AGENT_MAX_COST) {
    config.maxCost = Number(process.env.AGENT_MAX_COST);
  }

  if (process.env.SECOND_BRAIN_VAULT) {
    config.vaultDir = resolve(process.env.SECOND_BRAIN_VAULT);
  }

  if (overrides.display) {
    config.display = { ...config.display, ...overrides.display };
  }

  config = {
    ...config,
    ...overrides,
    display: config.display
  };

  if (!config.apiKey) {
    throw new Error('OPENROUTER_API_KEY is required.');
  }

  return config;
}
