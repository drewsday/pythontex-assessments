r"""The problem statement and the figure have to describe the same circuit.

KirchoffRules2 is the motivating case: four circuit elements are randomised
between `resistor=$R_D$` and `short`, while the statement always gives a value
for $R_D$.  The document builds, every value is printed, and the paper still
reaches students asking about a resistor that may not be in the drawing -- or
that appears four times.
"""

from __future__ import annotations

import re

CIRCUIT_RE = re.compile(r"\\begin\{circuitikz\}(.*?)\\end\{circuitikz\}", re.DOTALL)

# `$R_1=\SI{220}{\ohm}$` in the statement: a symbol the student is handed.
DECLARED_RE = re.compile(r"\$([A-Za-z]_[A-Za-z0-9]+)\s*=\s*\\SI\{")


def _declared_symbols(text: str) -> list[str]:
    """Symbols given a value in the prose, with the circuit bodies removed."""
    prose = CIRCUIT_RE.sub(" ", text)
    return sorted(set(DECLARED_RE.findall(prose)))


def _questions(text: str) -> list[tuple[str, str]]:
    """Pair each circuit with the statement belonging to it.

    A document can hold several questions, each with its own figure, and the
    same symbol may legitimately appear in more than one of them.  Comparing
    across the whole document would report those as duplicates, so slice the
    output at each circuit: a segment runs from one figure to the next and
    carries the "Given the following values" sentence that follows it.
    """
    starts = [m.start() for m in CIRCUIT_RE.finditer(text)]
    bounds = starts + [len(text)]
    segments = []
    for index, start in enumerate(starts):
        segment = text[start : bounds[index + 1]]
        circuit = CIRCUIT_RE.search(segment)
        if circuit:
            segments.append((circuit.group(1), segment))
    return segments


def _label_count(circuit: str, symbol: str) -> int:
    r"""How many circuit elements carry `$symbol$` as their label."""
    return len(re.findall(r"[=,\[]\s*\$" + re.escape(symbol) + r"\$", circuit))


def test_declared_symbols_appear_once_in_the_circuit(
    document, seeds, runs_cache, check_known
):
    """Every symbol given a value must label exactly one element in the figure."""
    check_known("symbols_match_diagram")

    offenders: list[str] = []
    checked_any = False

    for seed in seeds:
        text = runs_cache(document, seed).text
        for circuit_body, statement in _questions(text):
            checked_any = True
            for symbol in _declared_symbols(statement):
                count = _label_count(circuit_body, symbol)
                if count != 1:
                    offenders.append(
                        f"seed {seed}: {symbol} is given a value but labels "
                        f"{count} elements in the circuit"
                    )

    if not checked_any:
        return  # nothing with a generated circuit diagram

    affected_seeds = {o.split(":")[0] for o in offenders}
    assert not offenders, "statement/diagram mismatch on {} of {} seeds:\n  {}".format(
        len(affected_seeds),
        len(seeds),
        "\n  ".join(list(dict.fromkeys(offenders))[:6]),
    )
