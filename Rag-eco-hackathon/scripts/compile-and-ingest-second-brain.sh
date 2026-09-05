#!/usr/bin/env bash
# ── compile-and-ingest-second-brain.sh ──────────────────────────────────────
# Full Second Brain workflow:
#   1. (Optional, interactive) Agent compilation of new raw/ material
#   2. Wiki audit            — scripts/audit_wiki.py
#   3. Synapse ingestion     — scripts/sync_second_brain.py
#   4. Validation            — counts printed by the sync script
#
# Non-destructive: never deletes files, never overwrites indexed documents.
# The agent-compilation step is intentionally NOT automated — it requires an
# OpenRouter API key and interactive human approval for writes (preserved per
# the build manual). Run `npm start` in second-brain-agent/ to compile.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
fi

echo "═══ 1/4 Agent compilation ═══"
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  echo "OpenRouter key detected."
  if [ -d "$ROOT/../second-brain/raw" ] && [ "$(find "$ROOT/../second-brain/raw" -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
    echo "New material may be waiting in second-brain/raw/."
    echo "Compilation is an interactive, approval-gated step — run it now:"
    echo ""
    echo "    cd ../second-brain-agent && npm start"
    echo ""
    read -r -p "Compile now? (y/N) " ans
    if [[ "${ans,,}" == "y" ]]; then
      echo "Run the agent TUI in another terminal, then return here."
      read -r -p "Press Enter when compilation is done... " _
    fi
  else
    echo "No raw/ material pending — skipping compilation."
  fi
else
  echo "OPENROUTER_API_KEY not set — skipping agent compilation."
  echo "  (Set the key and run 'npm start' in second-brain-agent/ to compile raw/ → wiki/.)"
fi

echo ""
echo "═══ 2/4 Wiki audit ═══"
if "$PY" scripts/audit_wiki.py; then
  echo "Audit passed."
else
  echo ""
  echo "WARNING: audit found problems. Review second-brain/output/wiki-audit.md."
  echo "Continuing with ingestion (it only ADDS missing documents)."
fi

echo ""
echo "═══ 3/4 Synapse ingestion (additive re-sync) ═══"
"$PY" scripts/sync_second_brain.py --domain second_brain

echo ""
echo "═══ 4/4 Done ═══"
echo "Second Brain is in sync with Synapse."
echo "Start the app with ./start.sh and query the second_brain domain."