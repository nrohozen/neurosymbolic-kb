% code.lp - schema for the Python-codebase domain (domain 2).
%
% Standard term: an Answer Set Program (ASP). The SAME inference engine used for domain 1
% injects the AST-extracted facts (defines / calls / imports / inherits / layer) and
% combines them with the rules below. This is domain 2's hand-authored typed schema: it
% declares relation PROPERTIES (transitive closures over calls / imports / inherits) and
% the INTEGRITY CONSTRAINTS whose violation = a deductive contradiction with zero LLM calls
% (an inheritance cycle, and an ArchUnit-style layering rule: core must not import harness).

% ---------- call reachability: transitive closure of `calls` ----------
reaches(A,B) :- calls(A,B).
reaches(A,C) :- reaches(A,B), calls(B,C).

% ---------- import reachability: transitive closure of `imports` ----------
imports_trans(A,B) :- imports(A,B).
imports_trans(A,C) :- imports_trans(A,B), imports(B,C).

% ---------- inheritance: transitive closure ----------
inherits_trans(A,B) :- inherits(A,B).
inherits_trans(A,C) :- inherits_trans(A,B), inherits(B,C).

% ---------- integrity constraints = the deductive immune system ----------
% inheritance must be acyclic (Python forbids inheritance cycles)
:- inherits_trans(X,X).
% layering (ArchUnit-style): a core module must not import a harness module,
% directly or transitively.
:- imports_trans(M1,M2), layer(M1,core), layer(M2,harness).

% ---------- surface the deductive closure ----------
#show reaches/2.
#show imports_trans/2.
#show inherits_trans/2.
