% isa.lp - the only logical properties of "is a kind of": transitive + acyclic.
% These are properties of the RELATION, not facts about any class (no answer key here).
% A cycle in the witness's asserted edges = a self-contradiction the cross-examiner can catch.
is_a(X,Z) :- is_a(X,Y), is_a(Y,Z).
:- is_a(X,X).
#show is_a/2.
