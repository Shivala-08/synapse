"""LLM integration — priority order:
  1. NVIDIA NIM  (if NVIDIA_API_KEY is set in .env)
  2. Ollama      (local, no API key needed)
  3. Smart fallback (direct chunk formatting, no LLM)

NVIDIA NIM uses an OpenAI-compatible REST API so only the `openai` package
is required (already common in RAG stacks).
"""

import json
import re
import os
from typing import Optional, Generator
from loguru import logger

from src.config import settings


# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are Synapse, a knowledge intelligence assistant. "
    "You answer questions using ONLY retrieved document context. "
    "Never fabricate facts. Always cite sources using [Source N] labels. "
    "Keep your answer concise and direct (strictly 1-3 sentences). "
    "Answer ONLY what is asked; do not list unrelated details. "
    "Respond ONLY with valid JSON — no markdown fences, no extra text."
)

RAG_PROMPT = """Retrieved context:

=== DOCUMENT CONTEXT ===
{context}

=== KNOWLEDGE GRAPH RELATIONSHIPS ===
{graph_context}

=== QUESTION ===
{question}

Answer using ONLY the context above. Return ONLY this JSON object (pure JSON, no fences):
{{
  "answer": "<concise, direct 1-3 sentence answer citing [Source N] labels>",
  "confidence": "<High|Medium|Low>",
  "key_points": ["<key point 1>", "<key point 2>", "<key point 3>"],
  "entities_mentioned": ["<entity IDs found in context>"]
}}

Confidence rules:
- High   → direct, clear answer present in context
- Medium → partial or indirect information available
- Low    → context is insufficient or unrelated
If context is empty or irrelevant say so clearly in the answer field.
"""


# ── NVIDIA NIM client with key rotation ───────────────────────────────────────

class NvidiaLLM:
    """NVIDIA NIM LLM with automatic key rotation.

    Tries up to 10 API keys in order. Supports two .env formats:
      1. Individual: NVIDIA_API_KEY_1=nvapi-xxx, NVIDIA_API_KEY_2=nvapi-yyy, ...
      2. Comma-separated: NVIDIA_NIM_API_KEYS=nvapi-xxx,nvapi-yyy,...
    If a key fails (rate-limit, quota, auth error) it immediately tries the
    next one. Falls through to Ollama / smart-fallback if all keys fail.
    """

    def __init__(self):
        self.model = settings.nvidia_model
        self.base_url = settings.nvidia_base_url

        # Collect keys from individual config fields
        raw_keys = [
            settings.nvidia_api_key_1,
            settings.nvidia_api_key_2,
            settings.nvidia_api_key_3,
            settings.nvidia_api_key_4,
            settings.nvidia_api_key_5,
            settings.nvidia_api_key_6,
            settings.nvidia_api_key_7,
            settings.nvidia_api_key_8,
            settings.nvidia_api_key_9,
            settings.nvidia_api_key_10,
        ]
        self._keys = [k.strip() for k in raw_keys if k and k.strip()]

        # Fallback: parse comma-separated NVIDIA_NIM_API_KEYS from env
        if not self._keys:
            env_keys = os.getenv("NVIDIA_NIM_API_KEYS", "")
            if env_keys:
                self._keys = [k.strip() for k in env_keys.split(",") if k.strip()]
                logger.info(
                    f"NVIDIA NIM — parsed {len(self._keys)} key(s) from "
                    f"NVIDIA_NIM_API_KEYS env var"
                )

        if self._keys:
            logger.info(
                f"NVIDIA NIM ready — {len(self._keys)} key(s) loaded, "
                f"model: {self.model}"
            )
        else:
            logger.info("No NVIDIA_API_KEY_* set — NVIDIA NIM disabled.")

    @property
    def available(self) -> bool:
        return len(self._keys) > 0

    def _build_extra_body(self, is_nemotron: bool, enable_thinking: bool,
                          reasoning_budget: int) -> dict:
        """Build the extra_body dict for Nemotron thinking-mode parameters."""
        if not is_nemotron:
            return {}
        body = {"chat_template_kwargs": {"enable_thinking": enable_thinking}}
        if enable_thinking:
            body["reasoning_budget"] = reasoning_budget
        return body

    def _find_working_client(self, target_model: str, prompt: str,
                             max_tokens: int, enable_thinking: bool,
                             reasoning_budget: int, timeout: float = None,
                             start_key_idx: int = 0):
        if timeout is None:
            timeout = settings.nvidia_timeout_generate
        """Try each API key starting from start_key_idx until one succeeds; yield (idx, completion).

        Yields a single tuple on the first successful API call, then returns.
        Raises RuntimeError if all keys are exhausted.
        """
        from openai import OpenAI, AuthenticationError, RateLimitError, APIError

        last_error: Optional[Exception] = None
        is_nemotron = "nemotron" in target_model.lower()
        extra_body = self._build_extra_body(is_nemotron, enable_thinking, reasoning_budget)

        for idx in range(start_key_idx + 1, len(self._keys) + 1):
            api_key = self._keys[idx - 1]
            try:
                logger.info(
                    f"NVIDIA NIM — key {idx}/{len(self._keys)} "
                    f"(model: {target_model}, is_nemotron={is_nemotron}, "
                    f"enable_thinking={enable_thinking})"
                )
                client = OpenAI(base_url=self.base_url, api_key=api_key)
                completion = client.chat.completions.create(
                    model=target_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=1,
                    top_p=0.95,
                    max_tokens=max_tokens,
                    extra_body=extra_body if extra_body else None,
                    stream=True,
                    timeout=(settings.nvidia_timeout_connect, timeout),
                )
                yield idx, completion
                return

            except AuthenticationError as e:
                logger.warning(f"NVIDIA key {idx} — AuthenticationError: {e}. Trying next key.")
                last_error = e
            except RateLimitError as e:
                logger.warning(f"NVIDIA key {idx} — RateLimitError: {e}. Trying next key.")
                last_error = e
            except APIError as e:
                logger.warning(f"NVIDIA key {idx} — APIError: {e}. Trying next key.")
                last_error = e
            except Exception as e:
                logger.warning(f"NVIDIA key {idx} — Unexpected error: {e}. Trying next key.")
                last_error = e

        raise RuntimeError(
            f"All {len(self._keys)} NVIDIA API key(s) failed. "
            f"Last error: {last_error}"
        )

    def generate(self, prompt: str, max_tokens: int = 640, enable_thinking: bool = True, reasoning_budget: int = 1024, model: Optional[str] = None) -> str:
        """Try each API key in order, accumulate tokens, return full answer.

        The read timeout defaults to nvidia_timeout_generate (120s): the deep
        model can take 40s+ to first token, so anything below that guarantees
        every non-streaming deep query fails into the smart fallback.
        """
        target_model = model or self.model
        start_key_idx = 0
        last_error = None

        while start_key_idx < len(self._keys):
            try:
                for idx, completion in self._find_working_client(
                    target_model, prompt, max_tokens, enable_thinking, reasoning_budget,
                    timeout=settings.nvidia_timeout_generate, start_key_idx=start_key_idx
                ):
                    start_key_idx = idx - 1
                    answer_parts = []
                    for chunk in completion:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        reasoning = getattr(delta, "reasoning_content", None)
                        if reasoning:
                            logger.debug(f"[thinking] {reasoning}")
                        if delta.content:
                            answer_parts.append(delta.content)
                    return "".join(answer_parts)
            except Exception as e:
                logger.warning(f"Error during execution with NVIDIA key {start_key_idx + 1}: {e}. Retrying next key.")
                last_error = e
                start_key_idx += 1

        raise RuntimeError(f"All NVIDIA keys exhausted. Last error: {last_error}")

    def stream_generate(self, prompt: str, max_tokens: int = 640,
                        enable_thinking: bool = True, reasoning_budget: int = 1024,
                        model: Optional[str] = None) -> Generator[str, None, None]:
        """Yield answer tokens one-by-one as they arrive from NVIDIA NIM.

        Key rotation only happens BEFORE the first token is yielded. Once the
        user has seen partial output, retrying with another key would replay
        the answer from scratch and produce garbled duplicated text — so we
        propagate the error instead and let the caller surface it.
        """
        target_model = model or self.model
        start_key_idx = 0
        last_error = None
        yielded_any = False

        while start_key_idx < len(self._keys):
            try:
                for idx, completion in self._find_working_client(
                    target_model, prompt, max_tokens, enable_thinking, reasoning_budget,
                    timeout=settings.nvidia_timeout_stream, start_key_idx=start_key_idx
                ):
                    start_key_idx = idx - 1
                    for chunk in completion:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        reasoning = getattr(delta, "reasoning_content", None)
                        if reasoning:
                            logger.debug(f"[thinking] {reasoning}")
                        if delta.content:
                            yielded_any = True
                            yield delta.content
                    return
            except Exception as e:
                if yielded_any:
                    logger.error(
                        f"NVIDIA stream failed MID-STREAM with key {start_key_idx + 1}: {e}. "
                        "Not retrying — partial output already delivered."
                    )
                    raise
                logger.warning(f"Error during stream execution with NVIDIA key {start_key_idx + 1}: {e}. Retrying next key.")
                last_error = e
                start_key_idx += 1

        raise RuntimeError(f"All NVIDIA keys exhausted in stream. Last error: {last_error}")



# ── Ollama client (local fallback) ─────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434"

PREFERRED_MODELS = [
    "llama3.2", "llama3.1", "llama3",
    "mistral", "phi3", "phi",
    "gemma2", "gemma", "llama2", "orca-mini",
]


class OllamaLLM:
    """Minimal Ollama HTTP client (uses only the `requests` library)."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        import requests as _requests
        self._requests = _requests
        self.base_url = base_url.rstrip("/")
        self.model: Optional[str] = None
        self._detect_model()

    def _detect_model(self):
        """Ping Ollama and choose the best available model."""
        try:
            resp = self._requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code != 200:
                return
            available = [m["name"] for m in resp.json().get("models", [])]
            if not available:
                return
            logger.info(f"Ollama available models: {available}")
            for pref in PREFERRED_MODELS:
                for name in available:
                    if pref in name.lower():
                        self.model = name
                        logger.info(f"Selected Ollama model: {self.model}")
                        return
            self.model = available[0]
            logger.info(f"Using first available Ollama model: {self.model}")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")

    @property
    def available(self) -> bool:
        return self.model is not None

    def generate(self, prompt: str, max_tokens: int = 640) -> str:
        """Call Ollama generate and return raw response string."""
        import requests as _requests
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.05,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }
        resp = _requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120,  # generous timeout for local LLM inference
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


# ── JSON parsing ───────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """Parse JSON from LLM output with multiple fallback strategies."""
    raw = raw.strip()

    # 1. Strip <think>…</think> reasoning blocks (Qwen, DeepSeek-R1)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r"<reasoning>.*?</reasoning>", "", raw, flags=re.DOTALL).strip()

    # 2. Strip markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    # 3. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 4. Extract first complete {...} block
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if 0 <= start < end:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass

    # 5. Raise — triggers smart fallback upstream
    logger.warning(
        f"_extract_json: could not parse LLM output (len={len(raw)}). "
        "Raw snippet: " + raw[:200]
    )
    raise ValueError("Could not parse LLM response into JSON.")


# ── Smart fallback (no LLM) ────────────────────────────────────────────────────

def _smart_fallback(question: str, chunks: list, graph_context: list) -> dict:
    """Build a structured answer directly from retrieved chunks — no LLM needed."""
    if not chunks:
        return {
            "answer": (
                "No relevant documents found in the corpus for your query. "
                "Please open the **Control & Setup Panel** tab and click "
                "**Scan & Index Default Corpus** first."
            ),
            "confidence": "Low",
            "key_points": [],
            "entities_mentioned": [],
        }

    parts, key_points = [], []
    for i, c in enumerate(chunks[:4], 1):
        doc = c.get("citation", c.get("doc_id", "Unknown"))
        text = c.get("text", c.get("excerpt", "")).strip()[:500]
        parts.append(f"**[Source {i}] {doc}**\n{text}")
        key_points.append(text[:110] + "…")

    answer = "\n\n".join(parts)
    if graph_context:
        answer += "\n\n**Related graph connections:**\n" + "\n".join(
            f"• {g}" for g in graph_context[:5]
        )

    return {
        "answer": answer,
        "confidence": "Medium",
        "key_points": key_points[:3],
        "entities_mentioned": [],
    }


# ── Singletons ─────────────────────────────────────────────────────────────────

_nvidia_llm: Optional[NvidiaLLM] = None
_ollama_llm: Optional[OllamaLLM] = None


def get_llm():
    """Return the best available LLM: NVIDIA NIM → Ollama → None."""
    global _nvidia_llm, _ollama_llm

    # NVIDIA NIM (preferred when API key is present)
    if _nvidia_llm is None:
        _nvidia_llm = NvidiaLLM()
    if _nvidia_llm.available:
        return _nvidia_llm

    # Ollama local fallback
    if _ollama_llm is None:
        _ollama_llm = OllamaLLM()
    return _ollama_llm


def reset_llm():
    """Force re-initialisation of both LLM clients (e.g. after key update)."""
    global _nvidia_llm, _ollama_llm
    _nvidia_llm = None
    _ollama_llm = None



