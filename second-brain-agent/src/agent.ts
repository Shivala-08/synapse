import { OpenRouter, stepCountIs } from '@openrouter/agent';
import { loadConfig } from './config.js';
import { buildSystemPrompt } from './system-prompt.js';
import { buildTools } from './tools/index.js';
import { FileStateAccessor } from './state.js';

export interface AgentRunOptions {
  model?: string;
  onText?: (text: string) => void;
  /** State accessor for approval gates and multi-turn persistence */
  stateAccessor?: FileStateAccessor;
  /** Tool call IDs to approve when resuming from awaiting_approval */
  approveToolCalls?: string[];
  /** Tool call IDs to reject when resuming from awaiting_approval */
  rejectToolCalls?: string[];
}

export async function runAgent(
  input: string,
  options: AgentRunOptions = {},
) {
  const config = loadConfig();

  const client = new OpenRouter({
    apiKey: config.apiKey,
  });

  const model = options.model ?? config.model;
  const systemPrompt = buildSystemPrompt(config);
  const tools = buildTools();

  // Build callModel input with state accessor for approval gates
  const callInput: Record<string, unknown> = {
    model,
    instructions: systemPrompt,
    input,
    tools,
    stopWhen: stepCountIs(config.maxSteps),
    allowFinalResponse: true,
    doomLoop: true,
  };

  // Wire up state accessor if provided (enables approval workflow)
  if (options.stateAccessor) {
    callInput.state = options.stateAccessor;
  }

  // Resume with approval/rejection if provided
  if (options.approveToolCalls && options.approveToolCalls.length > 0) {
    callInput.approveToolCalls = options.approveToolCalls;
  }
  if (options.rejectToolCalls && options.rejectToolCalls.length > 0) {
    callInput.rejectToolCalls = options.rejectToolCalls;
  }

  const response = client.callModel(callInput as any);

  if (options.onText) {
    for await (const delta of response.getTextStream()) {
      options.onText(delta);
    }
  }

  return response;
}
