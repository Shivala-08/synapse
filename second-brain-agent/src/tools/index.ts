import { serverTool } from '@openrouter/agent';
import { fileReadTool } from './file-read.js';
import { fileWriteTool } from './file-write.js';
import { fileEditTool } from './file-edit.js';
import { globTool } from './glob.js';
import { grepTool } from './grep.js';
import { listDirTool } from './list-dir.js';
import { shellTool } from './shell.js';
import { ragQueryTool } from './rag-query.js';

export function buildTools() {
  return [
    fileReadTool,
    fileWriteTool,
    fileEditTool,
    globTool,
    grepTool,
    listDirTool,
    shellTool,
    ragQueryTool,

    serverTool({
      type: 'openrouter:web_search'
    }),

    serverTool({
      type: 'openrouter:datetime',
      parameters: {
        timezone: 'Asia/Kolkata'
      }
    })
  ];
}
