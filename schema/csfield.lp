% csfield.lp - schema for the "computer science as a field" domain (domain 4).
%
% Standard term: an Answer Set Program (ASP), run by the SAME inference engine as domains
% 1-3. This is the first WEAK-oracle domain: claims can't be run or parsed, so the deductive
% layer settles only what follows from a small high-confidence axiom set, and the LLM-judge
% ensemble handles the rest. The two relations are strict partial orders, so a cycle is a
% deductive contradiction (zero LLM calls) -- the structure the weak oracle leans on.
%
%   subfield_of(X,Y) - X is a subfield of Y (ml subfield_of ai)
%   subsumes(X,Y)    - technique/result X generalizes Y

% ---------- subfield_of: transitive, acyclic ----------
subfield_of(X,Z) :- subfield_of(X,Y), subfield_of(Y,Z).
:- subfield_of(X,X).   % acyclic: any cycle derives X subfield_of X (covers all lengths)

% ---------- subsumes: transitive, acyclic ----------
subsumes(X,Z) :- subsumes(X,Y), subsumes(Y,Z).
:- subsumes(X,X).

#show subfield_of/2.
#show subsumes/2.
