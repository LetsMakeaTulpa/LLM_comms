# llm_comms — the AI mesh envelope tool

Any AI to any AI, via copy-paste. No APIs, no auth keys, no rate limits, no vendor that can ban you.

The envelope is the product. The transport is you — pasting a markdown file between chats. The tool makes the payload correct, gradeable, and searchable.

## Why

Moving work between AI systems (Claude, Qwen, DeepSeek, Kimi, local models...) by pasting works, but it fails three ways: context bloat (whole sessions shipped when a paragraph would do), ungraded returns (an AI's "it works" is a claim, not a gate), and no memory (nobody remembers which model is actually good at what).

llm_comms fixes all three with one file format and five commands.

## Install

Single file, stdlib only, Python 3.8+:

```bash
git clone https://github.com/LetsMakeaTulpa/LLM_comms.git
cd LLM_comms
python3 llm_comms.py --help
```

Mesh home defaults to `./mesh` — override with `LLM_COMMS_HOME`.

## The envelope

```markdown
---
id: 0001
from: vibe
to: qwen
date: 2026-11-09T22:01:09Z
---

# HANDOFF

## TASK
Review this diff for security issues; done-when every changed function has an eyeball verdict.

## CONTEXT
Repo: LLM_comms. Single-file Python CLI.

## RETURN FORMAT
plain markdown

## BOUNDARY
Do not rewrite the file; verdicts only.
```

Envelope rules: TASK is one verb, one object, one done-when. CONTEXT is compressed state — the receiver re-reads durable knowledge, never ships whole sessions. BOUNDARY is what NOT to do (scope, persona, privacy limits). Markdown-plain so any model on earth can parse it.

## Commands

```bash
# compose a handoff — prints the file + paste instructions
python3 llm_comms.py send --to qwen --task "Review this diff; done-when every function has a verdict" \
    --context "Repo: LLM_comms" --boundary "verdicts only, no rewrites"

# paste the envelope into the qwen chat. when it answers:

# check any envelope is well-formed (exit 1 if not)
python3 llm_comms.py validate mesh/0001_vibe_to_qwen.md

# grade the return — claim-verification verdicts, logged
python3 llm_comms.py grade mesh/0001_vibe_to_qwen.md --verdict VERIFIED --notes "all functions checked"

# continue the exchange — swaps from/to, links reply-to
python3 llm_comms.py reply mesh/0001_vibe_to_qwen.md --task "Here is the review"

# the mesh's memory — which node got what, and how it graded
python3 llm_comms.py log [--node qwen]
```

## The verdicts (grade every return)

| Verdict | Meaning |
|---|---|
| `VERIFIED  | checked independently; two concordant credible sources or direct execution |
| `SUPPORTED  | one credible source or a single clean run; reasonable but unconfirmed |
| `CONTESTED` | credible sources disagree — report the conflict, don't average it away |
| `STALE` | the date check fails — a guess wearing a date |
| `UNSOURCED` | "studies show" with no study named — don't build on it |

An AI's output is a claim. Grading returns before they enter your stack is the whole discipline.

## The log is the mesh's memory

Every graded exchange lands in `mesh/log.jsonl` with from, to, task, verdict, and notes. Over weeks, `llm_comms.py log` becomes evidence — which models are actually good at what. Strength routing with receipts instead of vibes.

## Design principles

- **No vendors** — a tool banned one of us before; this stack hard-requires nothing. A new AI joins the mesh the moment it can read a markdown file.
- **Paste transport on purpose** — v1 is manual so it can never break; the envelope files are the wire format for scripted relay later.
- **Prompts are advisory, validators are authoritative** — hat tip to [llm-handoff](https://github.com/choughton/llm-handoff), kindred prior art for CLI-coding workflows.

## Verify (run the gate)

```bash
bash tests/verify.sh
```

Sends an envelope, validates it, proves a broken one fails, grades a return, and shows the log. Exit 0 = the tool is telling the truth.

## Roadmap

- `stats` — per-node grade aggregates from the log (strength routing, computed)
- scripted relay — envelope files as the wire format for automated model-to-model pipelines
- `pack` — multi-envelope bundles for campaign-sized exchanges
