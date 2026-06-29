"""Milestone 2 scorecard: the extraction path.

Tests one falsifiable claim (DIRECTION.md, metrics 6-9): a frozen base can populate the
typed graph, and the deductive solver recovers extraction precision for FREE by dropping
the contradiction-shaped extraction errors -- zero LLM calls -- at near-zero cost to recall.

The scoring math (`evaluate`) is pure and unit-tested offline; `main` adds the live
extraction over the corpus (needs a local Ollama; SKIPPED if unreachable). It reports the
M2 baseline (6/7) and the post-canonicalization numbers (metrics 13/14, M2.1) side by side.

Run:  python -m eval.run_m2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set

from eval.extraction_corpus import load_corpus
from eval.run_m1 import _verdict
from src.canonicalization import Canonicalizer
from src.extraction_filter import consistency_filter
from src.inference_engine import InferenceEngine
from src.knowledge_graph import KnowledgeGraph, Triple
from src.relation_extraction import RelationExtractor

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "ads.lp"
SEEDS = ROOT / "schema" / "seeds.jsonl"


@dataclass
class M2Scores:
    n_extracted: int
    n_gold: int
    precision_raw: float
    recall_raw: float
    n_kept: int
    n_dropped: int
    precision_filt: float
    recall_filt: float
    retention: float
    false_drops: int  # gold triples the filter wrongly dropped


def _dedup_by_atom(candidates: Iterable[Triple]) -> List[Triple]:
    seen: Set[str] = set()
    out: List[Triple] = []
    for t in candidates:
        a = t.as_atom()
        if a not in seen:
            seen.add(a)
            out.append(t)
    return out


def evaluate(
    engine: InferenceEngine,
    seed_atoms: Sequence[str],
    gold_atoms: Set[str],
    candidates: Iterable[Triple],
) -> M2Scores:
    uniq = _dedup_by_atom(candidates)
    extracted = {t.as_atom() for t in uniq}
    correct_raw = extracted & gold_atoms
    precision_raw = len(correct_raw) / len(extracted) if extracted else 0.0
    recall_raw = len(correct_raw) / len(gold_atoms) if gold_atoms else 0.0

    fr = consistency_filter(engine, seed_atoms, uniq)
    kept = {t.as_atom() for t in fr.kept}
    dropped = {t.as_atom() for t in fr.dropped}
    correct_filt = kept & gold_atoms
    precision_filt = len(correct_filt) / len(kept) if kept else 0.0
    recall_filt = len(correct_filt) / len(gold_atoms) if gold_atoms else 0.0
    retention = (recall_filt / recall_raw) if recall_raw > 0 else 1.0

    return M2Scores(
        n_extracted=len(extracted),
        n_gold=len(gold_atoms),
        precision_raw=precision_raw,
        recall_raw=recall_raw,
        n_kept=len(fr.kept),
        n_dropped=len(fr.dropped),
        precision_filt=precision_filt,
        recall_filt=recall_filt,
        retention=retention,
        false_drops=len(dropped & gold_atoms),
    )


def main() -> int:
    engine = InferenceEngine.from_schema_file(SCHEMA)
    try:
        engine.run([])
    except ImportError:
        print("clingo is not installed.  pip install -r requirements.txt")
        return 1

    kg = KnowledgeGraph.from_seeds(SEEDS)
    seed_atoms = kg.atoms()
    corpus = load_corpus()
    gold_atoms = {t.as_atom() for e in corpus for t in e.gold}

    extractor = RelationExtractor()
    candidates: List[Triple] = []
    for e in corpus:
        candidates.extend(extractor.extract(e.text, source=e.id))

    print("=" * 68)
    print("  Milestone 2 scorecard  (domain 1: extraction path + canonicalization)")
    print("=" * 68)
    print(f"  corpus={len(corpus)} texts  gold-triples={len(gold_atoms)}  "
          f"seeds={len(seed_atoms)}")
    print("-" * 68)

    if not candidates:
        print("  no candidates extracted -> SKIPPED (is Ollama running at :11434?)")
        print("=" * 68)
        return 0

    # canonicalize: entity-link + map to the controlled vocabulary (drops unmappable)
    canon = Canonicalizer.from_seed_triples(kg.triples)
    canon_candidates = [t for t in (canon.canonicalize(c) for c in candidates) if t is not None]

    s_raw = evaluate(engine, seed_atoms, gold_atoms, candidates)        # M2 baseline (6/7)
    s_can = evaluate(engine, seed_atoms, gold_atoms, canon_candidates)  # post-canon (13/14)

    v13 = _verdict(s_can.precision_raw, 0.80, 0.60)
    v14 = _verdict(s_can.recall_raw, 0.70, 0.50)

    print(f"  extracted={s_raw.n_extracted}  ->  canonicalized={s_can.n_extracted}  "
          f"(dropped-unmappable={s_raw.n_extracted - s_can.n_extracted})")
    print("-" * 68)
    print(f"   6. precision (pre-canon)  {s_raw.precision_raw:5.2f}    [M2 baseline]")
    print(f"   7. recall    (pre-canon)  {s_raw.recall_raw:5.2f}    [M2 baseline]")
    print(f"  13. canon precision        {s_can.precision_raw:5.2f}    go>=0.80 kill<0.60   -> {v13}")
    print(f"  14. canon recall           {s_can.recall_raw:5.2f}    go>=0.70 kill<0.50   -> {v14}")
    print("-" * 68)
    print(f"  canonicalization lift: precision {s_raw.precision_raw:+.2f}->{s_can.precision_raw:.2f}"
          f"  recall {s_raw.recall_raw:+.2f}->{s_can.recall_raw:.2f}")
    print(f"  post-canon consistency filter: dropped {s_can.n_dropped} "
          f"(false drops={s_can.false_drops}), precision {s_can.precision_raw:.2f} -> "
          f"{s_can.precision_filt:.2f}, zero LLM calls")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
