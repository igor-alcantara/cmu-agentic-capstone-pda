"""Local index over synthetic role and competency documents.

Stands in for the internal RAG index. Documents are markdown with a small
YAML-style frontmatter block; chunks follow the document's own ``##``
sections, so a chunk is one coherent topic rather than a fixed window of
tokens. Scoring is TF-IDF cosine: offline, deterministic, and good enough on
a synthetic corpus where the safeguards around retrieval matter more than the
embedding.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pda.models import RoleDocChunk


@dataclass
class RoleDoc:
    doc_id: str
    role: str
    department: str
    kind: str  # role_profile | competency_matrix | gap_guide
    updated: date
    sections: list[tuple[str, str]] = field(default_factory=list)


def parse_role_doc(path: Path) -> RoleDoc:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError(f"{path.name}: missing frontmatter")
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"')
    body = m.group(2)
    sections: list[tuple[str, str]] = []
    for part in re.split(r"^## ", body, flags=re.M):
        part = part.strip()
        if not part:
            continue
        title, _, content = part.partition("\n")
        if content.strip():
            sections.append((title.strip(), content.strip()))
    return RoleDoc(doc_id=path.stem, role=meta["role"], department=meta["department"],
                   kind=meta.get("kind", "role_profile"), updated=date.fromisoformat(meta["updated"]),
                   sections=sections)


class RoleDocIndex:
    def __init__(self, docs_dir: Path) -> None:
        self.docs: list[RoleDoc] = [parse_role_doc(p) for p in sorted(Path(docs_dir).glob("*.md"))]
        self.chunks: list[RoleDocChunk] = []
        for d in self.docs:
            for title, content in d.sections:
                self.chunks.append(RoleDocChunk(doc_id=d.doc_id, role=d.role, department=d.department,
                                                updated=d.updated, section=title, text=content))
        self._vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self._matrix = self._vec.fit_transform([f"{c.section}. {c.text}" for c in self.chunks])
        self.search_calls = 0

    def docs_for_role(self, role: str) -> list[RoleDoc]:
        return [d for d in self.docs if d.role.lower() == role.lower()]

    def search(self, query: str, k: int, role: str | None = None) -> list[RoleDocChunk]:
        """Top-k chunks by cosine similarity, optionally restricted to one role's docs."""
        self.search_calls += 1
        sims = cosine_similarity(self._vec.transform([query]), self._matrix)[0]
        order = sorted(range(len(self.chunks)), key=lambda i: -sims[i])
        out: list[RoleDocChunk] = []
        for i in order:
            c = self.chunks[i]
            if role is not None and c.role.lower() != role.lower():
                continue
            out.append(c.model_copy(update={"similarity": float(sims[i])}))
            if len(out) >= k:
                break
        return out
