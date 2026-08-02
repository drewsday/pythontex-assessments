"""Independent recomputation of the answer keys.

Each checker re-derives the answers from the values printed on the paper, using
physics written from the circuit or figure rather than copied from the document.
Copying the document's own expression here would only assert that it equals
itself; the point is to catch an algebra or unit error in the source.

Checkers are registered per document because the mapping from key positions to
quantities differs between assessments -- KirchoffRules1, for instance, reports
a battery current alongside two resistor currents, so a blanket "V[i] = I[i]*R[i]"
assumption would be wrong rather than merely incomplete.
"""

from __future__ import annotations

import math
import re

import pytest

from pytexlib import REPO_ROOT, run_document

RTOL = 0.01  # keys are formatted to 3 significant figures
G = 9.81


def _close(got: float, expected: float) -> bool:
    return math.isclose(got, expected, rel_tol=RTOL, abs_tol=1e-9)


def _round_bound(value: float, sigfigs: int = 3) -> float:
    """Largest absolute error introduced by printing `value` to `sigfigs`."""
    if value == 0:
        return 1e-12
    exponent = math.floor(math.log10(abs(value)))
    return 0.5 * 10 ** (exponent - (sigfigs - 1))


def _consistent(got: float, expected: float, *operands: float) -> bool:
    """Compare two quantities that were each reconstructed from rounded values.

    Checks like Kirchhoff's current law combine numbers already rounded to three
    significant figures, so the rounding errors add.  Comparing those sums with a
    plain relative tolerance produces false alarms whenever a small quantity is
    the difference of two larger ones -- the error stays tiny in absolute terms
    but is large next to the result.  Allow exactly the accumulated rounding
    slack and nothing more, so a genuine physics error is still caught.
    """
    slack = sum(_round_bound(v) for v in (got, expected, *operands))
    return abs(got - expected) <= slack


def _labelled(text: str, symbol: str) -> float:
    r"""Read the value of e.g. `$R_1=\SI{220}{\ohm}$` out of a problem statement."""
    pattern = re.compile(
        re.escape(symbol) + r"\s*=\s*\\SI\{(-?\d*\.?\d+(?:[eE][+-]?\d+)?)\}"
    )
    match = pattern.search(text)
    assert match, f"could not find {symbol} in the generated problem"
    return float(match.group(1))


def _key_values(result) -> list[float]:
    pattern = re.compile(r"\\SI\{(-?\d*\.?\d+(?:[eE][+-]?\d+)?)\}")
    return [float(v) for text in result.flat_solutions for v in pattern.findall(text)]


# ---------------------------------------------------------------------------
# DC_Circuits1: Va drives R1 in series with (R2 parallel R3).
# Key order: I1, I2, I3, V1, V2, V3.
# ---------------------------------------------------------------------------


def check_dc_circuits1(result) -> list[str]:
    va = _labelled(result.text, "$V_a")
    r1 = _labelled(result.text, "$R_1")
    r2 = _labelled(result.text, "$R_2")
    r3 = _labelled(result.text, "$R_3")
    i1, i2, i3, v1, v2, v3 = _key_values(result)[:6]

    req = r1 + 1 / (1 / r2 + 1 / r3)
    exp_i1 = va / req
    exp_v1 = exp_i1 * r1
    exp_v2 = va - exp_v1

    problems = []
    for name, got, expected in (
        ("I1", i1, exp_i1),
        ("V1", v1, exp_v1),
        ("V2", v2, exp_v2),
        ("V3", v3, exp_v2),
        ("I2", i2, exp_v2 / r2),
        ("I3", i3, exp_v2 / r3),
    ):
        if not _close(got, expected):
            problems.append(f"{name}: key says {got:g}, recomputed {expected:g}")

    # Kirchhoff current law at the parallel junction.
    if not _consistent(i1, i2 + i3, i2, i3):
        problems.append(f"KCL: I1={i1:g} but I2+I3={i2 + i3:g}")
    # Energy balance: the source supplies exactly what the resistors dissipate.
    # Powers go as I^2, so the rounding slack on each current roughly doubles.
    supplied = va * i1
    dissipated = i1**2 * r1 + i2**2 * r2 + i3**2 * r3
    if not math.isclose(supplied, dissipated, rel_tol=2 * RTOL, abs_tol=1e-9):
        problems.append(f"power: supplied {supplied:g} W, dissipated {dissipated:g} W")
    return problems


# ---------------------------------------------------------------------------
# KirchoffRules1: three branches between the same node pair -- (Va, R1),
# (R2 + R3), and an ideal Vb that fixes the node voltage.
# Key order: I1, I2, I3 (battery current), V1, V2, V3.
# ---------------------------------------------------------------------------


def check_kirchoff1(result) -> list[str]:
    va = _labelled(result.text, "$V_a")
    vb = _labelled(result.text, "$V_b")
    r1 = _labelled(result.text, "$R_1")
    r2 = _labelled(result.text, "$R_2")
    r3 = _labelled(result.text, "$R_3")
    i1, i2, i3, v1, v2, v3 = _key_values(result)[:6]

    exp_i1 = (va - vb) / r1
    exp_i2 = vb / (r2 + r3)

    problems = []
    for name, got, expected in (
        ("I1", i1, exp_i1),
        ("I2", i2, exp_i2),
        ("I3", i3, exp_i2 - exp_i1),
        ("V1", v1, exp_i1 * r1),
        ("V2", v2, exp_i2 * r2),
        ("V3", v3, exp_i2 * r3),
    ):
        if not _close(got, expected):
            problems.append(f"{name}: key says {got:g}, recomputed {expected:g}")

    # R2 and R3 are in series across the ideal battery.
    if not _consistent(v2 + v3, vb, v2, v3):
        problems.append(f"loop: V2+V3={v2 + v3:g} should equal Vb={vb:g}")
    # KCL at the top node: the two source branches feed the resistive branch.
    # I1 is negative here and I3 is its difference with I2, so this sum is a
    # small number built from larger ones -- exactly the case _consistent handles.
    if not _consistent(i1 + i3, i2, i1, i3):
        problems.append(f"KCL: I1+I3={i1 + i3:g} should equal I2={i2:g}")
    return problems


# ---------------------------------------------------------------------------
# CO4c: two spring questions on a frictionless surface, two on the hanging
# figure where theta is measured from the vertical, so 2*k*x*cos(theta) = m*g.
# ---------------------------------------------------------------------------


def check_co4c(result) -> list[str]:
    questions = re.findall(
        r"\\question (.*?)(?=\\question |\\end\{questions\})", result.text, re.DOTALL
    )
    answers = [soln for entry in result.solutions for soln in entry]
    assert len(questions) == len(answers), "question and answer counts disagree"

    number = r"(-?\d*\.?\d+(?:[eE][+-]?\d+)?)"
    problems = []
    for question, answer in zip(questions, answers):
        values = [float(v) for v in re.findall(r"\\SI\{" + number + r"\}", question)]
        angles = [int(a) for a in re.findall(r"\\ang\{(\d+)\}", question)]
        got = float(re.findall(r"\\SI\{" + number + r"\}", answer)[0])

        if "what is the spring constant?" in question:
            mass, stretch, accel = values
            expected, unit = mass * accel / stretch, r"\newton\per\meter"
        elif "frictionless surface" in question:
            k, stretch, accel = values
            expected, unit = k * stretch / accel, r"\kilogram"
        elif "How much has one of the springs" in question:
            k, mass = values
            expected = mass * G / (2 * k * math.cos(math.radians(angles[0])))
            unit = r"\meter"
        else:
            k, stretch = values
            expected = 2 * k * stretch * math.cos(math.radians(angles[0])) / G
            unit = r"\kilogram"

        if not _close(got, expected):
            problems.append(f"{question[:45]!r}: key {got:g}, recomputed {expected:g}")
        if unit not in answer:
            problems.append(f"{question[:45]!r}: answer should be in {unit}, got {answer}")
    return problems


CHECKERS = {
    "DC_Circuits1.tex": check_dc_circuits1,
    "KirchoffRules1.tex": check_kirchoff1,
    "KirchoffRules1/KirchoffRules1.tex": check_kirchoff1,
    "CO4c-Fall2021-PHYS201.tex": check_co4c,
}


@pytest.mark.parametrize("relpath", sorted(CHECKERS))
def test_answer_key_matches_independent_recomputation(relpath, seeds):
    checker = CHECKERS[relpath]
    path = REPO_ROOT / relpath

    failures = []
    for seed in seeds:
        result = run_document(path, seed)
        for problem in checker(result):
            failures.append(f"seed {seed}: {problem}")

    assert not failures, "{} disagreements over {} seeds:\n  {}".format(
        len(failures), len(seeds), "\n  ".join(failures[:8])
    )


def test_every_document_with_a_key_has_a_checker():
    """Fails loudly when a new assessment lands without physics coverage.

    This is the coverage ratchet: the point of the suite is that answer keys get
    verified, and a document with no checker is verified by nothing.
    """
    from pytexlib import doc_id, documents_with_code, extract_blocks

    unchecked = [
        doc_id(path)
        for path in documents_with_code()
        if any("addsoln" in block for block in extract_blocks(path))
        and doc_id(path) not in CHECKERS
    ]
    pytest.xfail(
        f"{len(unchecked)} assessments still have no independent answer-key "
        f"check: {', '.join(sorted(unchecked))}"
    )
