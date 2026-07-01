---
name: fuzzy-explore
description: Exploratory search for vague/no-target queries (e.g. "github agent projects", "what's hot in ai agents") where the user doesn't yet know what they want. Replaces single-shot star-biased search with FACET DISCOVERY — decomposes the vague topic into grounded sub-spaces (derived from a real taxonomy, never model prior), sweeps each facet with anti-popularity-bias params (sort=updated, stars cap, recency window), presents the sub-landscapes as a menu, then drills into the facet the user picks. Use BEFORE a broad/exploratory web-search or `gh search` when single-shot search would return popularity-bombarded top results. NOT for: targeted lookups (known name/URL — just search), typo/entity correction (query-craft), or single-answer factual questions.
origin: my-claude
---

# fuzzy-explore — Facet-Discovery Search for Vague Queries

A **procedural** skill (body is steps, not a prompt template) that runs **before**
broad/exploratory searches. It does not replace the search tool — it changes
*how* the search is shaped when the user has no fixed target.

## Why this exists

Agent search misses on **exploratory** queries are a different failure mode than
typo/ambiguity (that's `query-craft`). Here the user genuinely doesn't know what
they want — they're *browsing a landscape*, not *looking up a fact*.

Single-shot search is structurally wrong for this:

```
user: "搜 github 上 agent 的项目"   ← no target, just a space
agent: gh search "agent" --sort stars   ← ONE query, popularity-ranked
→ obra/superpowers (242k★), hermes-agent (206k★), opencode (180k★) ...
→ star-bomb: every old mega-repo drowns the new/niche ones the user wanted
```

Three mechanisms stack to cause the miss:

1. **Popularity bias** — `--sort stars` (and search-engine relevance) rewards
   old, high-traffic results. New/niche repos sink to the bottom, never seen.
2. **Single-shot query** — one query must cover a whole landscape. It can't.
   "agent" spans memory-agents, multi-agent orchestration, coding-agent CLIs,
   observability, cost-optimization — one string can't slice all of that.
3. **No target to validate against** — the agent can't tell "wrong result"
   from "right result" because the user doesn't have a target yet. So it
   can't self-correct; it just returns the popularity top-N and hopes.

The fix is not "guess harder what the user wants." The fix is **stop guessing —
reveal the landscape, let the user pick a sub-space, then drill.** The target
*grows* during the search; it isn't assumed up front.

## The shift

| | single-shot search | fuzzy-explore |
|---|---|---|
| assumes | user has a target | user has no target yet |
| query count | 1 | N (one per facet, in parallel) |
| ranking | popularity (stars/relevance) | recency + small-scale (anti-bias) |
| output | top-N results | a **menu of sub-landscapes** |
| convergence | none (return and hope) | user picks facet → drill-down loop |

## The Procedure (4 steps)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. GROUND FACETS  (anti-hallucination — same anchor as       │
│    query-craft's entity grounding)                           │
│    Decompose the vague topic into 3-5 sub-spaces. The facet  │
│    vocabulary MUST come from a real taxonomy, never from     │
│    model prior alone. Sources, in priority order:            │
│      a. OpenViking landscape docs for the domain             │
│         (e.g. agent ecosystem has 5: memory, orchestration,  │
│          observability, tool-use, cost/token)                │
│      b. codebase-memory graph clusters (get_architecture     │
│         'clusters' — de-facto modules of the field)          │
│      c. the query's own nouns as seed, expanded only against │ │
│         (a)/(b) — never free-associated.                     │
│    A wrong facet set (generic LLM taxonomy) reproduces       │
│    star-bomb in a new guise. Grounded facets escape it.      │
├──────────────────────────────────────────────────────────────┤
│ 2. ANTI-BIAS SWEEP  (parallel, one search per facet)         │
│    Each facet search applies the anti-popularity-bias levers:│
│      - sort=updated        (alive projects, not legacy stars)│
│      - stars cap (<500 or <1k)  (cut the mega-repos)         │
│      - created recency (>=3-6mo)  (surface new work)         │
│      - limit 3-5 per facet  (a sample, not a dump)           │
│    Run all facet searches in one parallel batch. No barrier  │
│    between facets — they're independent.                     │
├──────────────────────────────────────────────────────────────┤
│ 3. PRESENT MENU  (the "grow the target" step)                │
│    Show the user the sub-landscapes side by side, each with  │
│    2-3 representative hits (name, 1-line desc, star count    │
│    so the scale is visible). Format:                         │
│      Facet A — <label>: hit1, hit2, hit3                     │
│      Facet B — <label>: hit1, hit2, hit3                     │
│      ...                                                     │
│      "哪个子空间更接近你要的?选一个我往下钻。"                │
│    Ask exactly ONE question (the facet pick). Never a wall   │
│    of N final results — the user can't evaluate N random     │
│    repos without the sub-space label to organize them.       │
├──────────────────────────────────────────────────────────────┤
│ 4. DRILL-DOWN CONVERGE                                       │
│    After the user picks a facet: narrow into it. More        │
│    queries within that sub-space (related topics, the        │
│    picked repos' dependencies/inspirations, deeper recency). │
│    Loop step 2-3 within the chosen facet until the user      │
│    says "this one" — then return the focused result set.     │
└──────────────────────────────────────────────────────────────┘
```

## The anti-star-bomb levers (the actual mechanism)

This is the engineering core. The facet decomposition organizes results;
**these params are what actually escapes popularity bias**:

- `--sort updated` over `--sort stars` — recency beats legacy fame
- `stars:<N` cap — exclude mega-repos that always win on volume
- `created:>=YYYY-MM-DD` — restrict to new work (tunable window)
- small `--limit` per facet — a *sample* of the landscape, not a ranked dump

For web-search (not `gh`): the equivalent is biasing toward recency-filtered
results, excluding the usual top domains, and deliberately issuing variant
queries per facet rather than one canonical query.

## When to Activate

Trigger when ALL of:
- The query is **broad/exploratory** ("agent projects", "what's hot in X",
  "find me libraries for Y" where Y is a field not a name)
- The user has **no fixed target** (can't name the specific thing they want)
- Single-shot search would return **popularity-bombarded** top results

Do NOT activate for:
- Targeted lookup (known name/URL/repo — just search directly)
- Typo/entity collision (→ `query-craft`)
- Single-answer factual question (→ normal search)
- The user already named a sub-space ("memory agents for cli" — that's a
  facet already chosen, skip to step 2 with one facet)

## Gotchas (field-tested, from a live 4-facet run)

- **Don't over-stack facet query terms.** A facet query like
  `persistent agent memory vector sqlite` (5 words, implicit AND) returns
  **zero hits** — too strict. The anti-bias work is done by *params*
  (`--sort updated`, `stars:` cap, `created:`), NOT by piling keywords.
  Keep facet queries to 2-3 substance words; let the params narrow.
  *Observed: 5-word facet queries → empty; 2-3 word → signal.*
- **`gh` star/recency qualifiers are not 100% reliable when mixed.** A query
  combining `language:X` + `stars:<N` + multiple keywords silently dropped
  the `stars:<1000` filter (a 15k★ repo came through). Always **second-pass
  check** star counts on returned results; don't trust the qualifier alone.
- **The signal lives in facet INTERSECTIONS, not single facets.** One facet
  (extreme-new-small) is a noise pool; another (coding-cli) has star-bomb
  residue. Their *intersection* (new + coding + coordination theme) is
  where the real active sub-space surfaced. The menu's job is to make
  intersections visible — don't read facets in isolation.
- **An empty facet is data, not a bug.** 0 hits means the facet term was
  too narrow OR the sub-space is genuinely sparse. Loosen to 2 words
  before declaring the sub-space dead.

## Constraints (hard)

- **Facet grounding is non-negotiable.** Facets derive from a real taxonomy
  (OpenViking landscape docs / codebase-memory clusters). Free-associated
  LLM facets reproduce star-bomb with extra steps.
- **One question per menu.** The only ask is the facet pick. Never "which of
  these 15 repos?" — the sub-space label is what makes repos evaluable.
- **Anti-bias params on every facet sweep.** A facet search without
  `sort=updated` + star cap is just N single-shot searches = N star-bombs.
- **No new dependencies, single file, prompt-first.** v1 is the procedure
  above driven by hand; no orchestration framework. The parallel sweep is
  the caller batching tool calls, not a workflow engine.

## v1 Scope (intentionally small)

- Covers: exploratory repo/topic discovery on GitHub + web, grounded facets,
  one round of menu → drill-down
- Does NOT cover: automatic taxonomy *discovery* (v1 uses an existing
  grounded taxonomy source; auto-deriving facets from first-pass result
  clustering is the real hard part — deferred), within-facet relevance
  ranking (still the search engine's default, biased by recency instead of
  stars), multi-round convergence loop (v1 = one drill-down, not a deep tree)

## Out of v1 (logged, not built)

- **Auto-facet discovery** — clustering a first-pass broad search's results
  to *derive* the facet taxonomy on the fly (no pre-existing landscape docs
  needed). This is the actual research-grade piece; needs usage data first.
- **Convergence detection** — knowing when "the user has found it" without
  asking. v1 asks explicitly.
- **Cross-engine facet portability** — v1 levers are gh-shaped; mapping to
  exa/tavily/web-search recency filters is mechanical but unbuilt.
- **Composition with query-craft** — a dirty facet query (typo in the
  sub-space term) should route through query-craft first. v1 assumes clean
  facet terms; the compose is a one-line guard, deferred to avoid coupling.

## Self-Check (mental, runnable as a demo)

```
# ponytail: one assert-shaped demo, no framework
# Baseline (FAILS): single-shot star search on a vague query
gh search repos agent --sort stars --limit 5
#   → obra/superpowers, hermes-agent, opencode ... (star-bomb, useless for discovery)

# fuzzy-explore (WORKS): grounded facets, anti-bias sweep, menu
gh search repos "agent memory context" --sort updated --limit 3          # facet A
gh search repos "multi-agent orchestration" --sort updated --limit 3     # facet B
gh search repos "agent created:>=2025-03-01 stars:<500" --sort updated --limit 3  # facet C (new/niche)
gh search repos "coding agent cli" --sort updated --limit 3              # facet D
#   → aria-knowledge(16★), Gunita(0★), kairix(2★) ... real niche, invisible to baseline
#   present A/B/C/D as menu → user picks → drill into that sub-space
```
