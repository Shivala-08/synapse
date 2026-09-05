import readline from 'node:readline';
import { runAgent } from './agent.js';
import { loadConfig } from './config.js';
import { FileStateAccessor } from './state.js';
import { resolve } from 'path';

const config = loadConfig();

let currentModel = config.model;

// Create a file-backed state accessor for approval gates
const stateAccessor = new FileStateAccessor(resolve(config.sessionDir));

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: true,
});

function printBanner() {
  console.log('');
  console.log('╔══════════════════════════════════════════════╗');
  console.log('║              SECOND BRAIN AGENT              ║');
  console.log('║          OpenRouter + Local Markdown         ║');
  console.log('╚══════════════════════════════════════════════╝');
  console.log('');
  console.log(`Model: ${currentModel}`);
  console.log(`Vault: ${config.vaultDir}`);
  console.log('');
  console.log('Commands:');
  console.log('  /model <model>  Change model');
  console.log('  /new            Start a new conversation');
  console.log('  /help           Show commands');
  console.log('  /quit           Exit');
  console.log('');
}

function askApproval(question: string): Promise<boolean> {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      const normalized = answer.trim().toLowerCase();
      resolve(normalized === 'y' || normalized === 'yes');
    });
  });
}

async function handleApprovalLoop(response: any): Promise<void> {
  // Check if the run paused for approval
  const state = response.getResponse ? await response.getResponse() : null;
  const convState = stateAccessor.getState();

  if (convState?.status === 'awaiting_approval' && convState.pendingToolCalls?.length) {
    for (const pending of convState.pendingToolCalls) {
      const toolName = pending.name;
      const args = JSON.stringify(pending.arguments, null, 2);

      console.log('\n');
      console.log('┌─────────────────────────────────────────────┐');
      console.log('│           APPROVAL REQUIRED                 │');
      console.log('├─────────────────────────────────────────────┤');
      console.log(`│ Tool: ${toolName}`);
      console.log(`│ Arguments:`);
      // Show args truncated for readability
      const argStr = args.length > 400 ? args.slice(0, 400) + '...' : args;
      console.log(argStr.split('\n').map((l: string) => `│   ${l}`).join('\n'));
      console.log('└─────────────────────────────────────────────┘');

      const approved = await askApproval('\n  Approve? (y/n) ');

      if (approved) {
        console.log('\n  ✓ Approved');
      } else {
        console.log('\n  ✗ Rejected');
      }

      // Resume the run with approval/rejection
      try {
        process.stdout.write('\nagent › ');

        const resumeResponse = await runAgent('', {
          model: currentModel,
          stateAccessor,
          approveToolCalls: approved ? [pending.id] : undefined,
          rejectToolCalls: approved ? undefined : [pending.id],
          onText: (text) => process.stdout.write(text),
        });

        console.log('\n');

        // Check if there are more approval gates
        await handleApprovalLoop(resumeResponse);
      } catch (error) {
        console.error('\n\n✗ Resume failed:');
        if (error instanceof Error) {
          console.error(error.message);
        } else {
          console.error(error);
        }
        console.log('');
      }
    }
  }
}

function prompt() {
  rl.question('you › ', async (input) => {
    const message = input.trim();

    if (!message) {
      prompt();
      return;
    }

    if (message === '/quit' || message === '/exit') {
      rl.close();
      return;
    }

    if (message === '/help') {
      console.log('');
      console.log('/model <model>  Change the active OpenRouter model');
      console.log('/new            Start a new conversation');
      console.log('/help           Show this help');
      console.log('/quit           Exit');
      console.log('');
      prompt();
      return;
    }

    if (message === '/new') {
      stateAccessor.reset();
      console.log('↻ New conversation.');
      prompt();
      return;
    }

    if (message.startsWith('/model ')) {
      const model = message.slice('/model '.length).trim();

      if (!model) {
        console.log(`Current model: ${currentModel}`);
      } else {
        currentModel = model;
        console.log(`✓ Model changed to: ${currentModel}`);
      }

      prompt();
      return;
    }

    try {
      process.stdout.write('\nagent › ');

      const response = await runAgent(message, {
        model: currentModel,
        stateAccessor,
        onText: (text) => process.stdout.write(text),
      });

      console.log('\n');

      // Handle approval gates if the run paused
      await handleApprovalLoop(response);

    } catch (error) {
      console.error('\n\n✗ Agent error:');

      if (error instanceof Error) {
        console.error(error.message);
      } else {
        console.error(error);
      }

      console.log('');
    }

    prompt();
  });
}

printBanner();
prompt();
