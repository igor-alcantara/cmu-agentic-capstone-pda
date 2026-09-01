"""Context Researcher: query the internal role-document index with the 3.1 safeguards.

Owns nothing but retrieval. Queries are composed by code from the role and
the gap skills. Each query runs through ``retrieval.safeguards.retrieve``,
so the metadata precondition is checked before any similarity search, and
every kept passage has passed a per-query relevance check.
"""
from __future__ import annotations

from pda.llm import LLM, MockLLM
from pda.models import Gap, PreconditionResult, RoleDocChunk
from pda.prompts import RELEVANCE_SYSTEM, relevance_user
from pda.retrieval.index import RoleDocIndex
from pda.retrieval.safeguards import RelevanceChecker, make_rare_term_checker, retrieve


def build_queries(role: str, gaps: list[Gap]) -> list[str]:
    queries = [f"What is the purpose of the {role} role and which certifications does it expect?"]
    for g in gaps:
        queries.append(f"How do I close a gap in {g.skill} for the {role} role?")
    return queries


def llm_checker(llm: LLM) -> RelevanceChecker:
    def check(query: str, chunk: RoleDocChunk) -> bool:
        answer = llm.complete("relevance", RELEVANCE_SYSTEM, relevance_user(query, chunk.section, chunk.text),
                              max_tokens=60)
        return answer.strip().upper().startswith("YES")
    return check


def research(index: RoleDocIndex, role: str, gaps: list[Gap], llm: LLM, *, top_k: int, keep_min: int,
             keep_max: int, floor: float, packet_cap: int = 8
             ) -> tuple[PreconditionResult, list[RoleDocChunk], list[str]]:
    checker = make_rare_term_checker(index) if isinstance(llm, MockLLM) else llm_checker(llm)
    queries = build_queries(role, gaps)
    merged: dict[tuple[str, str], RoleDocChunk] = {}
    precondition: PreconditionResult | None = None
    for q in queries:
        pre, chunks = retrieve(index, role, q, top_k=top_k, keep_min=keep_min, keep_max=keep_max,
                               floor=floor, checker=checker)
        precondition = precondition or pre
        if pre.status != "ok":
            return pre, [], queries  # settled by metadata; no point running the other queries
        for c in chunks:
            key = (c.doc_id, c.section)
            if key not in merged or c.similarity > merged[key].similarity:
                merged[key] = c
    kept = sorted(merged.values(), key=lambda c: -c.similarity)[:packet_cap]
    return precondition or PreconditionResult(status="ok"), kept, queries
