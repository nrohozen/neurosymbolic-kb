"""Tests for the domain-3 StateOracle and the staleness policy. Offline, no clingo, no
network (the snapshot provider is a plain dict)."""
from src.knowledge_graph import Triple
from src.oracle import Claim, OracleRouter, StateOracle
from src.staleness import changed_keys, should_requery, ttl_for

SNAP = {"pihole": {"secondary_dns": "10.0.0.53"},
        "proxmox": {"guests": [{"name": "api", "status": "running"}]}}


def _provider():
    return SNAP


def _state(k, v):
    return Claim(Triple(k, "observed", v), kind="state")


def test_state_oracle_reads_the_snapshot():
    o = StateOracle(_provider)
    assert o.adjudicate(_state("pihole.secondary_dns", "10.0.0.53")).holds is True
    assert o.adjudicate(_state("pihole.secondary_dns", "1.1.1.1")).holds is False
    assert o.adjudicate(_state("does.not.exist", "x")).holds is None


def test_router_dispatches_state_claims():
    router = OracleRouter([StateOracle(_provider)])
    v = router.adjudicate(_state("proxmox.guest.api.status", "running"))
    assert v.holds is True and v.source == "state"


def test_ttl_scales_with_volatility():
    assert ttl_for("high") < ttl_for("medium") < ttl_for("low")
    assert ttl_for("unknown") == ttl_for("medium")


def test_should_requery_at_ttl_boundary():
    assert should_requery(now=4, last_queried=0, ttl=4) is True
    assert should_requery(now=3, last_queried=0, ttl=4) is False


def test_changed_keys_detects_a_flipped_value():
    old = {"pihole": {"secondary_dns": "10.0.0.53"}}
    new = {"pihole": {"secondary_dns": "1.1.1.1"}}
    assert changed_keys(old, new) == {"pihole.secondary_dns"}
    assert changed_keys(old, old) == set()
