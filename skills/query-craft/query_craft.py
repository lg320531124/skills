#!/usr/bin/env python3
"""query-craft — pre-search query hygiene (implementation, v1).

Thin LLM layer that cleans a user's web-search query before it hits a search
tool. Detects typo/phonetic/entity collisions against GROUNDED entities (from
real context, never model prior), auto-rewrites high-confidence cases, asks
the user only on genuine multi-entity ambiguity. Engine-agnostic: outputs a
clean query string, never calls a search tool itself.

Spec: my-claude/skills/query-craft/SKILL.md (Prompt Template section).

Usage:
    export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY + OPENAI_BASE_URL
    export QC_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic
    export QC_MODEL=xopglm52
    python3 query_craft.py "Harms agent" --entities hermes-agent OpenViking
    python3 query_craft.py "rtk" --entities rtk-ai/rtk "RTK Rust Type Kit"
    python3 query_craft.py "react hooks" --entities hermes-agent
    python3 query_craft.py --self-check
"""
# ponytail: single-file, stdlib + one SDK. No framework, no config files.
# Ceiling: one LLM call per query (no batching/caching) — fine for v1 opt-in.

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable

PROMPT = """You are a pre-search query hygiene layer. Your ONLY job: clean the user's search input before it hits a web-search tool. You do NOT search yourself.

## Input
- user_query: {query}
- grounded_entities: {entities}

## Step 1 — Entity grounding check
If grounded_entities is empty AND the query contains a suspicious proper noun (looks misspelled, phonetically garbled, or non-English), do NOT guess a correction from your own prior. Output pass-through. A wrong correction is worse than the original typo.

## Step 2 — Classify into exactly one branch

(a) HIGH-CONFIDENCE COLLISION: user_query maps to exactly ONE grounded entity via edit-distance or phonetic similarity.
    -> Output: {{"action":"rewrite","query":"<corrected>","note":"corrected: <from>-><to>"}}

(b) GENUINE MULTI-ENTITY AMBIGUITY: user_query could map to >=2 grounded entities. Ask ONE question, max 2 candidates.
    -> Output: {{"action":"ask","candidates":["<X>","<Y>"],"question":"你是指 X 还是 Y?"}}

(c) CLEAN or UNRESOLVABLE: no collision, or nothing to match against. Pass original through unchanged.
    -> Output: {{"action":"passthrough","query":"<original>"}}

## Hard rules
- Only correct proper nouns/entities found in grounded_entities. Never expand keywords, never generate multiple query variants.
- Never resolve classic polysemy (Java language vs island). Out of scope.
- When torn between (a) and (c), choose (c). Conservative.
- Output ONLY the JSON object above. No prose.

## Examples
user_query="Harms agent", grounded_entities=["hermes-agent","OpenViking"]
-> {{"action":"rewrite","query":"hermes agent","note":"corrected: Harms->hermes"}}

user_query="openvaking", grounded_entities=["OpenViking","hermes-agent"]
-> {{"action":"rewrite","query":"OpenViking","note":"corrected: openvaking->OpenViking"}}

user_query="rtk", grounded_entities=["rtk-ai/rtk","RTK Rust Type Kit"]
-> {{"action":"ask","candidates":["rtk-ai/rtk","RTK Rust Type Kit"],"question":"你是指 rtk-ai/rtk 还是 RTK Rust Type Kit?"}}

user_query="那个项目", grounded_entities=[]
-> {{"action":"passthrough","query":"那个项目"}}

user_query="react hooks", grounded_entities=["hermes-agent"]
-> {{"action":"passthrough","query":"react hooks"}}
"""


@dataclass
class Result:
    action: str          # rewrite | ask | passthrough
    query: str | None
    candidates: list[str] | None
    question: str | None
    note: str | None

    def to_json(self) -> str:
        return json.dumps({k: v for k, v in {
            "action": self.action,
            "query": self.query,
            "candidates": self.candidates,
            "question": self.question,
            "note": self.note,
        }.items() if v is not None}, ensure_ascii=False)


def _call_llm(prompt: str) -> str:
    """One LLM call. Prefers Anthropic SDK (matches hermes gateway); falls back
    to OpenAI-compatible. Caller sets env; no hardcoded keys."""
    base = os.environ.get("QC_BASE_URL", "")
    model = os.environ.get("QC_MODEL", "xopglm52")
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic(
            base_url=base or None,
            api_key=os.environ["ANTHROPIC_API_KEY"],
        )
        resp = client.messages.create(
            model=model, max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    if os.environ.get("OPENAI_API_KEY"):
        import openai
        client = openai.OpenAI(
            base_url=base or os.environ.get("OPENAI_BASE_URL", None),
            api_key=os.environ["OPENAI_API_KEY"],
        )
        resp = client.chat.completions.create(
            model=model, max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
    raise SystemExit("no API key: set ANTHROPIC_API_KEY or OPENAI_API_KEY")


def _extract_json(text: str) -> dict:
    """LLM may wrap JSON in prose/code fence. Pull the first {...} block."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON in response: {text!r}")
    return json.loads(m.group(0))


def query_craft(user_query: str, entities: Iterable[str]) -> Result:
    """Pure decision layer. Returns the classified result; never searches."""
    ents = list(entities)
    prompt = PROMPT.format(
        query=user_query,
        entities=json.dumps(ents, ensure_ascii=False),
    )
    raw = _call_llm(prompt)
    obj = _extract_json(raw)
    return Result(
        action=obj.get("action", "passthrough"),
        query=obj.get("query"),
        candidates=obj.get("candidates"),
        question=obj.get("question"),
        note=obj.get("note"),
    )


# ---- self-check (runnable, no framework) ----
def _self_check():
    """Live LLM self-check. Requires API key in env. Skips if missing."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        print("[self-check] SKIPPED — no API key in env (set ANTHROPIC_API_KEY to run)")
        return 0
    cases = [
        ("Harms agent", {"hermes-agent"}, "rewrite", "hermes"),
        ("openvaking", {"OpenViking"}, "rewrite", "OpenViking"),
        ("react hooks", {"hermes-agent"}, "passthrough", None),
    ]
    failures = 0
    for q, ents, want_action, want_substr in cases:
        r = query_craft(q, ents)
        ok = r.action == want_action and (want_substr is None or (r.query and want_substr in r.query))
        mark = "ok" if ok else "FAIL"
        print(f"[{mark}] {q!r} -> action={r.action} query={r.query!r} note={r.note!r}")
        if not ok:
            failures += 1
    # ambiguity case: action=ask, ≥2 candidates
    r = query_craft("rtk", {"rtk-ai/rtk", "RTK Rust Type Kit"})
    ok = r.action == "ask" and r.candidates and len(r.candidates) >= 2
    print(f"[{'ok' if ok else 'FAIL'}] 'rtk' -> action={r.action} candidates={r.candidates}")
    if not ok:
        failures += 1
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILURES'}")
    return failures


def main():
    ap = argparse.ArgumentParser(description="pre-search query hygiene")
    ap.add_argument("query", nargs="?", help="user's raw search phrasing")
    ap.add_argument("--entities", nargs="*", default=[], help="grounded entities from real context")
    ap.add_argument("--self-check", action="store_true", help="run live LLM self-check")
    args = ap.parse_args()
    if args.self_check:
        sys.exit(_self_check())
    if not args.query:
        ap.error("query required (or use --self-check)")
    r = query_craft(args.query, args.entities)
    print(r.to_json())


if __name__ == "__main__":
    main()
