"""L5 provenance: every fact is stamped seed / extracted / derived, and provenance is
metadata, not identity. Offline (stub transport; no network, no clingo)."""
from pathlib import Path

from src.knowledge_graph import KnowledgeGraph, Provenance, Triple
from src.relation_extraction import RelationExtractor

SEEDS = Path(__file__).resolve().parents[1] / "schema" / "seeds.jsonl"


def test_provenance_is_not_part_of_triple_identity():
    bare = Triple("quicksort", "is_a", "sorting_algorithm")
    stamped = Triple("quicksort", "is_a", "sorting_algorithm", provenance=Provenance("seed"))
    assert bare == stamped
    assert hash(bare) == hash(stamped)
    assert len({bare, stamped}) == 1  # dedups across provenance


def test_from_seeds_stamps_seed_provenance():
    kg = KnowledgeGraph.from_seeds(SEEDS)
    methods = {t.provenance.method for t in kg if t.provenance}
    assert methods == {"seed"}
    assert len(list(kg)) == len(kg)  # all stamped


def test_extractor_stamps_extracted_with_source():
    def stub(url, payload):
        return {"message": {"content": '{"s": "heapsort", "r": "is_a", "o": "sorting_algorithm"}'}}

    ext = RelationExtractor(transport=stub)
    triples = ext.extract("Heapsort is a sorting algorithm.", source="heapsort")
    assert len(triples) == 1
    prov = triples[0].provenance
    assert prov.method == "extracted" and prov.detail == "heapsort"
