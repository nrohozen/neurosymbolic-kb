% state.lp - schema for the homelab/infrastructure domain (domain 3).
%
% Standard term: an Answer Set Program (ASP), run by the SAME inference engine as domains
% 1 and 2. State is binary facts over a compound `resource.attribute` key, so it reuses
% `Triple` and the engine unchanged (binary predicates, like every prior domain):
%   observed(K,V) - the live system's current value for key K (from an MCP snapshot)
%   desired(K,V)  - the intended / known-good value for key K (hand-authored intent)
%
% CONFIG DRIFT is the product: a key whose observed value differs from its desired value.
% We DERIVE drift (rather than make it UNSAT) so a single run ENUMERATES every drifted key
% -- a drift is something to list and fix, not an impossible state. Genuinely impossible
% snapshots (a key with two observed or two desired values at once) stay integrity
% constraints (UNSAT), matching the deductive immune system of the other domains.

% ---------- config drift (derived, enumerable product) ----------
drift(K,Vobs) :- desired(K,V1), observed(K,Vobs), V1 != Vobs.

% ---------- integrity constraints: an impossible snapshot ----------
:- observed(K,V1), observed(K,V2), V1 != V2.
:- desired(K,V1),  desired(K,V2),  V1 != V2.

#show drift/2.
