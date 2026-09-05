import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import type { ConversationState } from '@openrouter/agent';
import {
  createInitialState,
  serializeConversationState,
  deserializeConversationState,
} from '@openrouter/agent';

/**
 * File-backed StateAccessor for the OpenRouter agent SDK.
 *
 * Persists ConversationState to disk so that:
 * 1. Approval gates work (tools with requireApproval pause the run)
 * 2. Multi-turn conversations survive CLI restarts
 * 3. approveToolCalls / rejectToolCalls can resume a paused run
 */
export class FileStateAccessor {
  private filePath: string;
  private state: ConversationState | null = null;

  constructor(sessionDir: string, conversationId?: string) {
    const dir = resolve(sessionDir);
    mkdirSync(dir, { recursive: true });

    const id = conversationId || this.loadOrCreateId(dir);
    this.filePath = resolve(dir, `${id}.json`);

    // Pre-load existing state if present
    if (existsSync(this.filePath)) {
      try {
        const raw = readFileSync(this.filePath, 'utf-8');
        this.state = deserializeConversationState(raw);
      } catch {
        this.state = null;
      }
    }
  }

  private loadOrCreateId(dir: string): string {
    const idFile = resolve(dir, 'current-conversation-id.txt');
    if (existsSync(idFile)) {
      return readFileSync(idFile, 'utf-8').trim();
    }
    const id = crypto.randomUUID();
    writeFileSync(idFile, id, 'utf-8');
    return id;
  }

  /**
   * Load the current conversation state, or null if none exists.
   */
  load = async (): Promise<ConversationState | null> => {
    if (this.state) return this.state;

    if (existsSync(this.filePath)) {
      try {
        const raw = readFileSync(this.filePath, 'utf-8');
        this.state = deserializeConversationState(raw);
        return this.state;
      } catch {
        return null;
      }
    }
    return null;
  };

  /**
   * Save the conversation state to disk.
   */
  save = async (state: ConversationState): Promise<void> => {
    this.state = state;
    const json = serializeConversationState(state);
    writeFileSync(this.filePath, json, 'utf-8');
  };

  /**
   * Get the current state (for checking pendingToolCalls status).
   */
  getState(): ConversationState | null {
    return this.state;
  }

  /**
   * Reset state for a new conversation.
   */
  reset(): ConversationState {
    const newState = createInitialState();
    this.state = newState;
    return newState;
  }
}
