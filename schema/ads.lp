% ads.lp - schema for the Algorithms & Data Structures domain (domain 1).
%
% Standard term: this is an Answer Set Program (ASP). The inference engine injects
% the entity facts (from schema/seeds.jsonl and any candidate triple) and combines
% them with the rules below. This file is the project's hand-authored "innate prior" /
% typed schema: it declares relation PROPERTIES (transitivity, a total order, typed
% disjointness) and the INTEGRITY CONSTRAINTS whose violation = a deductive
% contradiction (detected with zero LLM calls).

% ---------- the complexity lattice (a declared total order) ----------
complexity_class(o_1).
complexity_class(o_logn).
complexity_class(o_n).
complexity_class(o_nlogn).
complexity_class(o_n2).
complexity_class(o_2n).

% covering chain: each class is one step cheaper than the next
faster_step(o_1,    o_logn).
faster_step(o_logn, o_n).
faster_step(o_n,    o_nlogn).
faster_step(o_nlogn,o_n2).
faster_step(o_n2,   o_2n).

% complexity_leq = reflexive-transitive closure of the chain
complexity_leq(C,C)   :- complexity_class(C).
complexity_leq(C1,C2) :- faster_step(C1,C2).
complexity_leq(C1,C3) :- complexity_leq(C1,C2), complexity_leq(C2,C3).
complexity_lt(C1,C2)  :- complexity_leq(C1,C2), C1 != C2.

% ---------- is_a: a transitive hierarchy ----------
is_a(X,Z) :- is_a(X,Y), is_a(Y,Z).

% ---------- faster_than: the comparison shape the project must answer ----------
% A is faster_than B iff A's (average-case, for M1) complexity class is strictly lower.
faster_than(A,B) :- has_complexity(A,CA), has_complexity(B,CB), complexity_lt(CA,CB).

% ---------- integrity constraints = the deductive immune system ----------
% the strict complexity order must stay antisymmetric (a cycle = contradiction)
:- complexity_lt(C1,C2), complexity_lt(C2,C1).
% the is_a hierarchy must be acyclic
:- is_a(X,Y), is_a(Y,X), X != Y.
% an entity carries a single (M1: average-case) complexity class
:- has_complexity(A,C1), has_complexity(A,C2), C1 != C2.
% typed-property disjointness
:- has_property(X,stable),   has_property(X,not_stable).
:- has_property(X,in_place), has_property(X,not_in_place).

% ---------- surface the deductive closure ----------
#show is_a/2.
#show complexity_leq/2.
#show complexity_lt/2.
#show faster_than/2.
#show has_complexity/2.
#show has_property/2.
