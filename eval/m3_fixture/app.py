"""M3 fixture module: a known call chain and inheritance chain (do not refactor — the M3
reachability gold in eval/m3_cases.jsonl depends on this exact structure).

Call graph:  main -> handle -> {validate -> normalize, save -> write}
Inheritance: leaf -> mid -> base
"""
from eval.m3_fixture.util import normalize, write


class Base:
    def run(self):
        ...


class Mid(Base):
    pass


class Leaf(Mid):
    pass


def main():
    handle()


def handle():
    validate()
    save()


def validate():
    normalize(1)


def save():
    write(1)
