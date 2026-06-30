"""Tests for the domain-3 snapshot extractor. Offline, no clingo, no network."""
from pathlib import Path

from src.state_extraction import captured_at, file_provider, observed_from_snapshot

SNAPSHOT = Path(__file__).resolve().parents[1] / "eval" / "m4_snapshot.json"


def _triples():
    snap = file_provider(SNAPSHOT)()
    return {(t.s, t.r, t.o) for t in observed_from_snapshot(snap)}, snap


def test_flattens_each_section_to_observed_triples():
    t, _ = _triples()
    assert ("pihole.secondary_dns", "observed", "10.0.0.53") in t
    assert ("pihole.dns.media.lan", "observed", "10.0.0.41") in t
    assert ("npm.proxy.media.example.foo.forward", "observed", "10.0.0.41:8080") in t
    assert ("npm.proxy.media.example.foo.enabled", "observed", "true") in t
    assert ("proxmox.guest.api.status", "observed", "running") in t


def test_captured_at_is_the_snapshot_timestamp():
    _, snap = _triples()
    assert captured_at(snap) == 1719600000


def test_provider_is_injectable_with_a_plain_dict():
    snap = {"pihole": {"secondary_dns": "1.2.3.4"}}
    t = {(x.s, x.r, x.o) for x in observed_from_snapshot(snap)}
    assert t == {("pihole.secondary_dns", "observed", "1.2.3.4")}
