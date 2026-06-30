"""Deterministic extraction of `observed` facts from a homelab MCP snapshot (domain 3).

A snapshot is a plain JSON dict (pihole / npm / proxmox sections, modeled on the MCP's
read-only list calls). `observed_from_snapshot` flattens it into binary `Triple`s over a
compound `resource.attribute` key, reusing the SAME `Triple` / `normalize` as every prior
domain (so `observed(K,V)` is binary, like all other relations).

The snapshot SOURCE is injectable (a `StateProvider` = a zero-arg callable returning the
dict): tests and the offline eval use a committed JSON file; a live provider that calls the
MCP is a later increment. Either way the deductive layer only ever sees a dict, so the eval
stays offline and deterministic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List

from src.knowledge_graph import Triple

StateProvider = Callable[[], dict]


def file_provider(path: str | Path) -> StateProvider:
    def _provider() -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return _provider


def captured_at(snapshot: dict) -> int:
    return int(snapshot.get("captured_at", 0))


def observed_from_snapshot(snapshot: dict) -> List[Triple]:
    """Flatten a snapshot into `observed(key, value)` triples (deterministic order)."""
    out: List[Triple] = []

    pihole = snapshot.get("pihole", {})
    if "secondary_dns" in pihole:
        out.append(Triple("pihole.secondary_dns", "observed", pihole["secondary_dns"]))
    for rec in pihole.get("dns_records", []):
        out.append(Triple(f"pihole.dns.{rec['domain']}", "observed", rec["ip"]))

    for host in snapshot.get("npm", {}).get("proxy_hosts", []):
        out.append(Triple(f"npm.proxy.{host['domain']}.forward", "observed", host["forward"]))
        out.append(
            Triple(f"npm.proxy.{host['domain']}.enabled", "observed", str(host["enabled"]).lower())
        )

    for guest in snapshot.get("proxmox", {}).get("guests", []):
        out.append(Triple(f"proxmox.guest.{guest['name']}.status", "observed", guest["status"]))

    return out
