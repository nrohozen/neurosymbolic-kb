% open.lp - schema for the open / contested-knowledge domain (domain 5).
%
% Standard term: an Answer Set Program (ASP), run by the SAME inference engine as domains
% 1-4. Domain 5 has no reliable oracle -- claims come from conflicting sources, and a
% contradiction here is NOT an error to reject but a DISAGREEMENT to represent. The schema's
% job is to surface conflicts -- including LATENT ones (no two claims conflict, but together
% they do) that pairwise surface-comparison misses.
%
%   broader_than(X,Y) - X is broader / more general than Y
%   same_as(X,Y)      - X and Y denote the same thing (identity / equivalence)

% ---------- broader_than: a strict partial order (transitive, acyclic) ----------
broader_than(X,Z) :- broader_than(X,Y), broader_than(Y,Z).
:- broader_than(X,X).   % a cycle (any length) = a (latent) disagreement to surface

% ---------- same_as: an equivalence (symmetric, transitive) ----------
same_as(X,Y) :- same_as(Y,X).
same_as(X,Z) :- same_as(X,Y), same_as(Y,Z).

% ---------- cross-relation disjointness ----------
% you can't be strictly broader than something you are identical to
:- broader_than(X,Y), same_as(X,Y).

#show broader_than/2.
#show same_as/2.
