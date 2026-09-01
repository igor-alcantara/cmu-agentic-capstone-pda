"""Checkpoint 3.1 safeguards: the deterministic layers do the work, not the score."""
from __future__ import annotations

import pytest

from pda.retrieval.index import RoleDocIndex
from pda.retrieval.safeguards import (keyword_overlap_checker, metadata_precondition, retrieve)
from tests.conftest import DATA


@pytest.fixture(scope="module")
def index() -> RoleDocIndex:
    return RoleDocIndex(DATA / "role_docs")


def _retrieve(index, role, query):
    return retrieve(index, role, query, top_k=8, keep_min=4, keep_max=6, floor=0.02,
                    checker=keyword_overlap_checker)


def test_no_role_doc_yields_labeled_fallback_not_similarity_guess(index):
    before = index.search_calls
    pre, chunks = _retrieve(index, "Solutions Engineer", "What AWS level does a Solutions Engineer need?")
    assert pre.status == "no_role_doc"
    assert chunks == []
    assert index.search_calls == before, "no similarity search may run when metadata says there is nothing to search"


def test_conflicting_role_docs_are_detected_deterministically(index):
    pre = metadata_precondition(index, "Qlik Developer")
    assert pre.status == "conflicting_docs"
    assert set(pre.doc_ids) == {"qlik_developer_role_profile", "qlik_developer_role_profile_2025"}
    pre_ok = metadata_precondition(index, "Data Engineer")
    assert pre_ok.status == "ok"


def test_metadata_filter_beats_similarity_on_wrong_role_bait(index):
    # E008 is an Analytics Consultant with Python and Data Modeling gaps. Those words are
    # far heavier in the Data Engineer documents, so unfiltered similarity picks the wrong role.
    query = "Python and data modeling expectations for this role"
    unfiltered = index.search(query, k=3)
    assert unfiltered[0].role == "Data Engineer", "the bait must actually work for the test to mean anything"
    pre, chunks = _retrieve(index, "Analytics Consultant", query)
    assert pre.status == "ok"
    assert chunks, "the filtered retrieval must still find relevant passages for the right role"
    assert all(c.role == "Analytics Consultant" for c in chunks)
    assert all(c.relevant for c in chunks)


def test_relevance_check_is_per_query_and_floor_is_only_coarse(index):
    pre, chunks = _retrieve(index, "Data Engineer", "How do I close a gap in Apache Spark?")
    assert chunks and any("Spark" in c.section or "Spark" in c.text for c in chunks)
    # a near-zero similarity chunk does not survive, but the floor is far below any real match
    assert all(c.similarity >= 0.02 for c in chunks)
    assert max(c.similarity for c in chunks) > 0.1
