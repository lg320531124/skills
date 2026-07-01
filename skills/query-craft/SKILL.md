---
name: query-craft
description: Pre-search query hygiene for web-search tools. Detects typo/phonetic/entity collisions in user input (e.g. "Harms agent"→hermes-agent, "openvaking"→OpenViking), auto-rewrites high-confidence cases, and asks the user to confirm only on genuine multi-entity ambiguity. Use BEFORE calling WebSearch/exa/grep when the user's phrasing may be misspelled, colloquial, or non-English. Engine-agnostic: outputs only a clean query string; the caller decides which search tool to run.
origin: my-claude
---

# query-craft — Pre-Search Query Hygiene

A thin layer **before** web-search tools. Not a search engine, not a search-execution skill (those are exa-search / deep-research / search-first). This skill only cleans the query: detects likely misspellings/phonetic/entity collisions, auto-rewrites when confident, asks the user only when genuinely ambiguous.

## Why this exists

Agent web-search misses are often a **query construction** problem, not a search-engine problem:

```
user (Chinese/colloquial/typo) → agent guesses → uses raw words as query → search misses
```

Examples from real sessions:
- "Harms agent" → should be `hermes-agent` (phonetic collision)
- "openvaking" → should be `OpenViking` (typo)
- "那个项目" → no referent resolvable (vague)

Existing frameworks ship no query-hygiene layer in front of web search:
- LangChain `RePhraseQueryRetriever` / `MultiQueryRetriever` — vectorstore-RAG only, no ambiguity detection
- LlamaIndex `query_transform` — only Identity/HyDE/Decompose, no `ClarifyQueryTransform`
- QueryGym / ConvGQR — IR-recall optimization (keyword expansion), wrong direction for web search
- CollabSearch — closest match, but monolithic MSc thesis, polysemy-only (Java/Apple/Tesla), not typo/phonetic

The three-axis intersection — **web-search-front + typo/entity ambiguity + auto-resolve-or-confirm** — is unoccupied. This skill fills it minimally.

## When to Activate

Trigger BEFORE calling a web-search tool (WebSearch / exa / grep) when the user's input may be:
- A misspelled or phonetically-garbled proper noun ("Harms agent", "openvaking")
- Colloquial / spoken-language phrasing that won't match indexed text
- Non-English (Chinese) where the search target is an English-named entity
- Vague reference ("那个", "the thing from last time")

Do NOT activate for:
- Clean, unambiguous queries — pass through unchanged (zero overhead)
- Queries where the user already gave an exact name/URL
- Code/package searches via package registries (search-first handles those)

## The Three-Branch Decision

Run this decision tree on the user's input:

```
┌─────────────────────────────────────────────────────────┐
│  1. ENTITY GROUNDING (mandatory, anti-hallucination)    │
│     Build candidate entities from REAL context only:    │
│     - cwd project dirs, git remotes                     │
│     - installed skills / plugins / MCP servers          │
│     - recently read files, recent conversation topics   │
│     - known GitHub repos mentioned this session         │
│     NEVER invent candidates from model prior alone.     │
│     A wrong correction is worse than no correction.     │
├─────────────────────────────────────────────────────────┤
│  2. CLASSIFY                                            │
│     (a) HIGH-CONFIDENCE COLLISION                       │
│         input maps to exactly ONE grounded entity       │
│         (edit-distance/phonetic match, e.g.            │
│         "Harms"→"hermes" given hermes-agent in cwd)     │
│         → AUTO-REWRITE, search with corrected query     │
│         → note the correction to user in one line       │
│                                                         │
│     (b) GENUINE MULTI-ENTITY AMBIGUITY                  │
│         input could map to ≥2 grounded entities          │
│         → ASK ONE question: "你是指 X 还是 Y?"          │
│         → max 2 candidates, never a wall of options     │
│         → after answer, search with confirmed query     │
│                                                         │
│     (c) CLEAN / UNRESOLVABLE                            │
│         no collision, or no grounded entity to match    │
│         → PASS THROUGH original query unchanged         │
└─────────────────────────────────────────────────────────┘
```

## Rewrite Rules (when auto-rewriting)

- Proper nouns: correct typos/phonetic collisions against grounded entities only
- Chinese → English entity name when the search target is English-named (keep Chinese if searching Chinese content)
- Strip filler ("那个", "帮我看看", "basically") — keep the substance
- Do NOT do keyword expansion / multi-query generation (that's MultiQueryRetriever / QueryGym territory, and it broadens the query — wrong direction for disambiguation)
- Do NOT resolve classic polysemy (Java language vs island) — out of scope; that's CollabSearch's domain

## Engine-Agnostic Output

This skill produces **only a clean query string** (plus optional one-line correction note). It does NOT call the search tool. The caller decides:
- WebSearch / exa / grep / firecrawl — caller's choice
- This keeps the skill thin and composable with exa-search / deep-research

## Constraints (hard)

- **Entity grounding is non-negotiable.** Corrections must trace to real context. Hallucinated entity correction silently misleads search — worse than the original typo.
- **Ask at most ONE question, max 2 candidates.** Never a wall of options (borrows career-ops interview mode's "Ask exactly ONE question at a time" guardrail).
- **Conservative threshold.** When uncertain between (a) and (c), pass through. False confirmations degrade UX and fight agent autonomy.
- **No new dependencies, no framework, single file.** v1 is opt-in; always-on PreToolUse hook is explicitly out of v1.

## v1 Scope (intentionally small)

- Covers: typo / phonetic / entity-name collisions only (the verified pain points)
- Does NOT cover: general query expansion, classic polysemy, multi-turn conversational coreference
- Opt-in: agent invokes when input looks dirty; no automatic interception

## Out of v1 (logged, not built)

- Always-on PreToolUse hook intercepting every search (costs one extra LLM call per search; false-positive interruptions annoying) — biggest form-factor risk, deferred
- Trigger-threshold tuning (the real hard part, not scaffolding) — needs usage data first
- Known-entity allowlist persistence across sessions

## Prompt Template (B — the engine)

Copy-paste this into the LLM when the skill activates. It IS the implementation
for the prompt-first v1 — no code, just this template driven by grounded context.

```
You are a pre-search query hygiene layer. Your ONLY job: clean the user's
search input before it hits a web-search tool. You do NOT search yourself.

## Input
- user_query: <the user's raw phrasing>
- grounded_entities: <entities harvested from REAL context — cwd project dirs,
  git remotes, installed skills/plugins/MCP servers, recently read files,
  topics from this session. May be empty.>

## Step 1 — Entity grounding check
If grounded_entities is empty AND the query contains a suspicious proper noun
(looks misspelled, phonetically garbled, or non-English), do NOT guess a
correction from your own prior. Output pass-through. A wrong correction is
worse than the original typo.

## Step 2 — Classify into exactly one branch

(a) HIGH-CONFIDENCE COLLISION: user_query maps to exactly ONE grounded entity
    via edit-distance or phonetic similarity (e.g. "Harms"→"hermes" when
    hermes-agent is in grounded_entities).
    → REWRITE to the corrected entity. Keep the rest of the query intact.
    → Output: {"action":"rewrite","query":"<corrected>","note":"corrected: <from>→<to>"}

(b) GENUINE MULTI-ENTITY AMBIGUITY: user_query could map to ≥2 grounded entities.
    → Ask ONE question, max 2 candidates. Never more.
    → Output: {"action":"ask","candidates":["<X>","<Y>"],"question":"你是指 X 还是 Y?"}

(c) CLEAN or UNRESOLVABLE: no collision, or nothing to match against.
    → Pass the original query through unchanged.
    → Output: {"action":"passthrough","query":"<original>"}

## Hard rules
- Only correct proper nouns/entities found in grounded_entities. Never expand
  keywords, never generate multiple query variants (that broadens — wrong
  direction for disambiguation).
- Never resolve classic polysemy (Java language vs island). Out of scope.
- When torn between (a) and (c), choose (c). Conservative.
- Output ONLY the JSON object above. No prose.

## Examples
user_query="Harms agent"
grounded_entities=["hermes-agent","OpenViking","codebase-memory-mcp"]
→ {"action":"rewrite","query":"hermes agent","note":"corrected: Harms→hermes"}

user_query="openvaking"
grounded_entities=["OpenViking","hermes-agent"]
→ {"action":"rewrite","query":"OpenViking","note":"corrected: openvaking→OpenViking"}

user_query="rtk"
grounded_entities=["rtk-ai/rtk","RTK Rust Type Kit"]
→ {"action":"ask","candidates":["rtk-ai/rtk","RTK Rust Type Kit"],"question":"你是指 rtk-ai/rtk 还是 RTK Rust Type Kit?"}

user_query="那个项目"
grounded_entities=[]
→ {"action":"passthrough","query":"那个项目"}

user_query="react hooks"
grounded_entities=["hermes-agent"]
→ {"action":"passthrough","query":"react hooks"}
```

### How to harvest grounded_entities (caller's job, before invoking the prompt)

- `ls` the cwd + parent; read git remotes (`git remote -v`) in nearby repos
- list installed skills/plugins/MCP servers from the session context
- scan recently read files + recent user/assistant topics in the conversation
- collect any GitHub `owner/repo` strings mentioned this session

This list is the anti-hallucination anchor. Bigger = safer corrections;
empty = force pass-through (never guess).

## Self-Check (runnable)

```
# ponytail: one assert-based demo, no framework
assert query_craft("Harms agent", entities={"hermes-agent"}) == ("hermes-agent", "corrected: Harms→hermes")
assert query_craft("那个项目", entities=set()) == (None, "pass-through: unresolvable, no grounded entity")
assert query_craft("react hooks", entities={"hermes-agent"}) == ("react hooks", "pass-through: clean")
# multi-entity ambiguity → returns candidates to ask, not a rewrite
assert query_craft("rtk", entities={"rtk-ai/rtk","RTK Rust Type Kit"}) == (None, "ask: 你是指 rtk-ai/rtk 还是 RTK Rust Type Kit?")
```
