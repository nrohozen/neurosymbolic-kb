"""Comparison-counting reference algorithms the ExecutionOracle runs to settle
performance claims empirically (the strong, deterministic oracle for domain 1).

Each function takes a list and returns the number of element comparisons performed.
Counts are deterministic for a fixed input, so the oracle is reproducible.
"""
from __future__ import annotations

from typing import Callable, Sequence


def bubblesort_ops(data: Sequence[int]) -> int:
    a = list(data)
    n = len(a)
    ops = 0
    for i in range(n):
        for j in range(n - 1 - i):
            ops += 1
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return ops


def insertion_sort_ops(data: Sequence[int]) -> int:
    a = list(data)
    ops = 0
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0:
            ops += 1
            if a[j] > key:
                a[j + 1] = a[j]
                j -= 1
            else:
                break
        a[j + 1] = key
    return ops


def mergesort_ops(data: Sequence[int]) -> int:
    ops = 0

    def merge(left, right):
        nonlocal ops
        out = []
        i = j = 0
        while i < len(left) and j < len(right):
            ops += 1
            if left[i] <= right[j]:
                out.append(left[i])
                i += 1
            else:
                out.append(right[j])
                j += 1
        out.extend(left[i:])
        out.extend(right[j:])
        return out

    def sort(a):
        if len(a) <= 1:
            return a
        mid = len(a) // 2
        return merge(sort(a[:mid]), sort(a[mid:]))

    sort(list(data))
    return ops


def quicksort_ops(data: Sequence[int]) -> int:
    a = list(data)
    ops = 0

    def sort(lo, hi):
        nonlocal ops
        if lo >= hi:
            return
        pivot = a[(lo + hi) // 2]
        i, j = lo, hi
        while i <= j:
            while i <= hi and a[i] < pivot:
                ops += 1
                i += 1
            while j >= lo and a[j] > pivot:
                ops += 1
                j -= 1
            if i <= j:
                a[i], a[j] = a[j], a[i]
                i += 1
                j -= 1
        sort(lo, j)
        sort(i, hi)

    sort(0, len(a) - 1)
    return ops


# name -> operation-count function. Keys match the entity constants in the schema.
REFERENCE_IMPLS: dict[str, Callable[[Sequence[int]], int]] = {
    "bubblesort": bubblesort_ops,
    "insertion_sort": insertion_sort_ops,
    "mergesort": mergesort_ops,
    "quicksort": quicksort_ops,
}
