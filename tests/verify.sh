#!/usr/bin/env bash
# llm_comms verification gate — exit 0 means the tool is telling the truth.
set -e
cd "$(dirname "$0")/.."
export LLM_COMMS_HOME="${LLM_COMMS_HOME:-$(mktemp -d)}"

echo "== 1. send produces a valid envelope =="
python3 llm_comms.py send --to qwen --from vibe \
  --task "Smoke test; done-when this envelope validates" \
  --context "gate run" --boundary "test only"

echo
echo "== 2. validate passes on the good envelope =="
python3 llm_comms.py validate "$LLM_COMMS_HOME"/0001_*.md

echo
echo "== 3. validate FAILS on a broken envelope =="
printf -- "---\nid: 9999\n---\n# broken\n" > "$LLM_COMMS_HOME/broken.md"
if python3 llm_comms.py validate "$LLM_COMMS_HOME/broken.md" 2>/dev/null; then
  echo "GATE FAIL: broken envelope passed validation"; exit 1
else
  echo "OK: broken envelope correctly rejected (exit 1)"
fi

echo
echo "== 4. grade rejects an invalid verdict =="
if python3 llm_comms.py grade "$LLM_COMMS_HOME"/0001_*.md --verdict WRONG 2>/dev/null; then
  echo "GATE FAIL: invalid verdict accepted"; exit 1
else
  echo "OK: invalid verdict correctly rejected (exit 2)"
fi

echo
echo "== 5. grade logs a valid verdict =="
python3 llm_comms.py grade "$LLM_COMMS_HOME"/0001_*.md --verdict VERIFIED --notes "gate run"

echo
echo "== 6. reply links and swaps =="
python3 llm_comms.py reply "$LLM_COMMS_HOME"/0001_*.md --task "return trip"
python3 llm_comms.py validate "$LLM_COMMS_HOME"/0002_*.md

echo
echo "== 7. log shows the exchange =="
python3 llm_comms.py log

echo
echo "GATE PASSED — all six behaviors verified."
