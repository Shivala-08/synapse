import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';

const RAG_API_URL = process.env.RAG_API_URL || 'http://localhost:8000';

export const ragQueryTool = tool({
  name: 'rag_query',
  description:
    'Query the Synapse RAG engine for answers backed by ingested documents. ' +
    'Uses hybrid vector search + knowledge graph + LLM to find and synthesize answers. ' +
    'Use this when the user asks about content that might be in the indexed documents ' +
    '(second-brain wiki articles, exam prep materials, or uploaded documents).',
  inputSchema: z.object({
    question: z.string().describe('The natural language question to search for'),
    domain_id: z
      .string()
      .optional()
      .describe(
        'Domain to search: "second_brain" for wiki articles, "exam_prep" for study materials. ' +
          'Omit to use the default domain.'
      ),
    routing_mode: z
      .enum(['auto', 'fast', 'deep'])
      .optional()
      .describe(
        'auto = let the system choose (default), fast = quick 8B model, deep = thorough 550B model'
      ),
  }),
  execute: async ({ question, domain_id, routing_mode }) => {
    try {
      const payload: Record<string, unknown> = {
        question,
        top_k: 5,
      };
      if (domain_id) payload.domain_id = domain_id;
      if (routing_mode) payload.routing_mode = routing_mode;

      const response = await fetch(`${RAG_API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(120_000),
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        return {
          error: `RAG API returned ${response.status}: ${text.slice(0, 500)}`,
        };
      }

      const data = await response.json();

      // Format a concise result for the agent
      const sources = (data.sources || [])
        .map(
          (s: any, i: number) =>
            `[${i + 1}] ${s.doc_id || 'unknown'} (score: ${s.distance != null ? (1 - s.distance).toFixed(3) : 'n/a'})`
        )
        .join('\n');

      const keyPoints = (data.key_points || []).map((kp: string) => `• ${kp}`).join('\n');

      return {
        answer: data.answer || 'No answer generated.',
        confidence: data.confidence ?? 'unknown',
        model_used: data.model_used || 'unknown',
        latency_ms: data.latency_ms ?? 0,
        sources: sources || 'No sources found.',
        key_points: keyPoints || 'None extracted.',
        entities_used: (data.entities_used || []).join(', ') || 'None',
        domain: data.domain || 'unknown',
      };
    } catch (err: any) {
      if (err?.name === 'TimeoutError' || err?.code === 'ABORT_ERR') {
        return {
          error:
            'RAG query timed out (>120s). The LLM may be loading. Try again in a moment.',
        };
      }
      return {
        error: `RAG query failed: ${err?.message || String(err)}. Is the FastAPI backend running on ${RAG_API_URL}?`,
      };
    }
  },
});
