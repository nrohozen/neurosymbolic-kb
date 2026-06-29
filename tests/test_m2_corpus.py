"""Guards the M2 extraction corpus: well-formed, in-schema, non-trivial. Offline."""
from eval.extraction_corpus import (
    ALLOWED_RELATIONS,
    COMPLEXITY_ENUM,
    load_corpus,
)


def test_corpus_is_non_trivial():
    entries = load_corpus()
    assert len(entries) >= 12
    # every entry has source text and at least one gold triple to find
    assert all(e.text.strip() and e.gold for e in entries)


def test_corpus_ids_are_unique():
    ids = [e.id for e in load_corpus()]
    assert len(ids) == len(set(ids))


def test_gold_triples_stay_within_the_m1_schema():
    for e in load_corpus():
        for t in e.gold:
            assert t.r in ALLOWED_RELATIONS, f"{e.id}: bad relation {t.r}"
            if t.r == "has_complexity":
                assert t.o in COMPLEXITY_ENUM, f"{e.id}: bad complexity {t.o}"
