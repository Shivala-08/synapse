"""One-off: populate domain knowledge graphs from already-stored chunks.

The wiki/PDF docs were ingested before domain-aware entity extraction existed,
so their graphs are empty. This re-runs extraction (with the domain profile)
over the chunks already persisted in the relational DB and writes the results
into the domain-scoped graph. Chroma is untouched.
"""
import sys
import pathlib
import sqlite3

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from src.config import load_domain_profile  # noqa: E402
from src.graph.knowledge_graph import get_knowledge_graph  # noqa: E402
from src.pipeline.extractor import extract_entities, extract_wikilinks  # noqa: E402

DB = pathlib.Path("data/synapse.db")


def domain_doc_ids(domain_id: str) -> list[str]:
    reg = pathlib.Path(f"data/documents_{domain_id}.json")
    if not reg.exists():
        return []
    import json
    return list(json.loads(reg.read_text()).keys())


def populate(domain_id: str) -> None:
    dp = load_domain_profile(domain_id)
    if not dp:
        print(f"no profile for {domain_id}")
        return
    doc_ids = domain_doc_ids(domain_id)
    if not doc_ids:
        print(f"no registered docs for {domain_id}")
        return
    kg = get_knowledge_graph(dp)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    total_nodes = 0
    for doc_id in doc_ids:
        cur.execute(
            "SELECT content FROM document_chunks WHERE doc_id = ?", (doc_id,)
        )
        contents = [r[0] for r in cur.fetchall()]
        if not contents:
            print(f"  skip {doc_id[:50]} (no chunks)")
            continue
        combined = "\n".join(contents)
        # Per-chunk extraction so entity_ids land on each chunk later if needed
        merged: dict[str, list] = {}
        for c in contents:
            r = extract_entities(c, domain_profile=dp)
            for cat, ents in r.items():
                if ents:
                    merged.setdefault(cat, []).extend(ents)
        # De-duplicate per category
        merged = {k: sorted(set(v)) for k, v in merged.items()}
        n = sum(len(v) for v in merged.values())
        kg.add_document_entities(doc_id, combined, merged, {})
        if dp.link_syntax == "wikilink":
            # The parser spaces out [[Note]] into [ [ Note ] ] in stored chunks,
            # so read the raw source file for genuine wikilink syntax when it
            # still exists on disk.
            links = extract_wikilinks(combined)
            src = pathlib.Path(dp.source_path) / doc_id
            if not links and src.exists():
                links = extract_wikilinks(src.read_text(errors="ignore"))
            if links:
                kg.add_wikilink_entities(doc_id, sorted(set(links)), doc_id=doc_id)
        print(f"  {doc_id[:50]}: {n} entities")
        total_nodes += n
    kg.save()
    print(f"{domain_id}: {kg.graph.number_of_nodes()} nodes, "
          f"{kg.graph.number_of_edges()} edges in DB")


if __name__ == "__main__":
    for d in sys.argv[1:] or ["second_brain", "exam_prep"]:
        print(f"== {d} ==")
        populate(d)