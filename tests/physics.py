"""Independent re-derivation of the answers for each kind of question.

Every solver here works from the values printed on the paper and physics written
from the circuit or figure. Copying the document's own expression would only
assert that it equals itself; the point is to catch an algebra or unit error in
the source.

Questions are keyed by type rather than by document because the assessments
compose the same handful of problems. CO10-CO11-CO12.tex, for instance, is
DC_Circuits1 followed by EquivalentResistance1 followed by KirchoffRules1, and
three documents share the same power-dissipation circuit. A per-document checker
would duplicate the physics once per file and let the copies drift.

Each entry states, in the order the answer key reports them, what the answers
should be and what unit each should carry.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable

K_COULOMB = 8.9875517873681764e9
MICRO = 1e-6

# A value paired with the unit the key is expected to report it in.
Answer = tuple[str, float, str]


# ---------------------------------------------------------------------------
# Reading values back off the printed page
# ---------------------------------------------------------------------------

_NUM = r"(-?\d*\.?\d+(?:[eE][+-]?\d+)?)"


def labelled(statement: str, symbol: str) -> float:
    r"""Value of e.g. `$R_1=\SI{220}{\ohm}$` in a problem statement."""
    match = re.search(re.escape(symbol) + r"\s*=\s*\\SI\{" + _NUM + r"\}", statement)
    if match is None:
        raise LookupError(f"no value for {symbol!r} in statement")
    return float(match.group(1))


def by_unit(statement: str, unit: str) -> list[float]:
    r"""Every `\SI{value}{unit}` in the statement carrying `unit`.

    Used where the document gives a quantity no symbol -- the light-bulb and
    vibrating-string questions state their values inline.
    """
    pattern = r"\\SI\{" + _NUM + r"\}\{" + re.escape(unit) + r"\}"
    return [float(v) for v in re.findall(pattern, statement)]


def series(*values: float) -> float:
    """Reciprocal sum: resistors in parallel, or capacitors in series."""
    return 1.0 / sum(1.0 / v for v in values)


# ---------------------------------------------------------------------------
# Solvers
# ---------------------------------------------------------------------------


def solve_series_parallel_3r(statement: str) -> list[Answer]:
    """R1 in series with (R2 parallel R3), across an ideal battery."""
    va = labelled(statement, "$V_a")
    r1, r2, r3 = (labelled(statement, f"$R_{i}") for i in (1, 2, 3))

    i1 = va / (r1 + series(r2, r3))
    v1 = i1 * r1
    v_parallel = va - v1
    return [
        ("I1", i1, r"\ampere"),
        ("I2", v_parallel / r2, r"\ampere"),
        ("I3", v_parallel / r3, r"\ampere"),
        ("V1", v1, r"\volt"),
        ("V2", v_parallel, r"\volt"),
        ("V3", v_parallel, r"\volt"),
    ]


def solve_two_battery_three_branch(statement: str) -> list[Answer]:
    """Three branches between one node pair: (Va, R1), (R2 + R3), and ideal Vb.

    The ideal battery fixes the node voltage at Vb, so the resistive branch and
    the Va branch are each determined independently, and the battery carries
    whatever current closes KCL.
    """
    va = labelled(statement, "$V_a")
    vb = labelled(statement, "$V_b")
    r1, r2, r3 = (labelled(statement, f"$R_{i}") for i in (1, 2, 3))

    i1 = (va - vb) / r1
    i2 = vb / (r2 + r3)
    return [
        ("I1", i1, r"\ampere"),
        ("I2", i2, r"\ampere"),
        ("I3 (battery)", i2 - i1, r"\ampere"),
        ("V1", i1 * r1, r"\volt"),
        ("V2", i2 * r2, r"\volt"),
        ("V3", i2 * r3, r"\volt"),
    ]


def solve_ladder_resistance(statement: str) -> list[Answer]:
    """Ladder between A and B: two R3 rungs, R2 at the far end, R1 everywhere.

    Working in from the far end: four R1 and R2 in series form the last loop,
    that sits in parallel with the far R3, four more R1 lead back to the near
    R3, and two R1 finish the run to the terminals.
    """
    r1, r2, r3 = (labelled(statement, f"$R_{i}") for i in (1, 2, 3))

    far_loop = 4 * r1 + r2
    middle = series(far_loop, r3) + 4 * r1
    total = series(middle, r3) + 2 * r1
    return [("Req", total, r"\ohm")]


def solve_three_parallel_two_series(statement: str) -> list[Answer]:
    """R1, R2, R3 all in parallel, in series with R4 and R5."""
    vb = labelled(statement, "$V_b")
    r1, r2, r3, r4, r5 = (labelled(statement, f"$R_{i}") for i in range(1, 6))

    i_series = vb / (series(r1, r2, r3) + r4 + r5)
    v4, v5 = i_series * r4, i_series * r5
    v_parallel = vb - v4 - v5
    return [
        ("V1", v_parallel, r"\volt"),
        ("V2", v_parallel, r"\volt"),
        ("V3", v_parallel, r"\volt"),
        ("V4", v4, r"\volt"),
        ("V5", v5, r"\volt"),
        ("I1", v_parallel / r1, r"\ampere"),
        ("I2", v_parallel / r2, r"\ampere"),
        ("I3", v_parallel / r3, r"\ampere"),
        ("I4", i_series, r"\ampere"),
        ("I5", i_series, r"\ampere"),
    ]


def solve_series_pair_power(statement: str) -> list[Answer]:
    """(R1 + R2) in parallel with R3, in series with R4. Reports powers too."""
    vb = labelled(statement, "$V_b")
    r1, r2, r3, r4 = (labelled(statement, f"$R_{i}") for i in range(1, 5))

    r12 = r1 + r2
    i4 = vb / (series(r12, r3) + r4)
    v4 = i4 * r4
    v_parallel = vb - v4
    i12 = v_parallel / r12
    i3 = v_parallel / r3
    return [
        ("V1", i12 * r1, r"\volt"),
        ("V2", i12 * r2, r"\volt"),
        ("V3", v_parallel, r"\volt"),
        ("V4", v4, r"\volt"),
        ("I1", i12, r"\ampere"),
        ("I2", i12, r"\ampere"),
        ("I3", i3, r"\ampere"),
        ("I4", i4, r"\ampere"),
        ("W1", i12**2 * r1, r"\watt"),
        ("W2", i12**2 * r2, r"\watt"),
        ("W3", i3**2 * r3, r"\watt"),
        ("W4", i4**2 * r4, r"\watt"),
    ]


def solve_light_bulbs(statement: str) -> list[Answer]:
    """Identical bulbs in parallel on a 120 V circuit, limited by the breaker.

    The breaker caps the total current, so the count is 120*I/P. A partial bulb
    cannot be connected, so the honest answer is the floor.
    """
    (power,) = by_unit(statement, r"\watt")
    (current,) = by_unit(statement, r"\ampere")
    return [("count", math.floor(120.0 * current / power), "")]


def solve_capacitor_network(statement: str) -> list[Answer]:
    """C1 in parallel with (C2 in series with C3), across an ideal battery.

    Charges and capacitances are reported in micro-units, energies in joules.
    """
    vb = labelled(statement, "$V_b")
    c1, c2, c3 = (labelled(statement, f"$C_{i}") * MICRO for i in (1, 2, 3))

    c23 = series(c2, c3)
    q_series = c23 * vb
    v2, v3 = q_series / c2, q_series / c3
    return [
        ("C123", (c23 + c1) / MICRO, r"\micro\farad"),
        ("Q1", (c1 * vb) / MICRO, r"\micro\coulomb"),
        ("Q2", q_series / MICRO, r"\micro\coulomb"),
        ("Q3", q_series / MICRO, r"\micro\coulomb"),
        ("V1", vb, r"\volt"),
        ("V2", v2, r"\volt"),
        ("V3", v3, r"\volt"),
        ("U1", 0.5 * c1 * vb**2, r"\joule"),
        ("U2", 0.5 * c2 * v2**2, r"\joule"),
        ("U3", 0.5 * c3 * v3**2, r"\joule"),
    ]


def solve_capacitor_equivalent(statement: str) -> list[Answer]:
    """C3+C4 and C5+C6 each in series, those two in parallel, all in series
    with C1, C2 and C7."""
    c = [labelled(statement, f"$C_{i}") * MICRO for i in range(1, 8)]
    c1, c2, c3, c4, c5, c6, c7 = c

    parallel_block = series(c3, c4) + series(c5, c6)
    return [("Ceq", series(c1, c2, parallel_block, c7) / MICRO, r"\micro\farad")]


def solve_efield_1d(statement: str) -> list[Answer]:
    """Three point charges on the x axis; field and force at the location of q.

    Every charge sits on the axis, so each contribution is purely horizontal:
    E_x = k*Q*(x - x_Q)/|x - x_Q|^3, which is k*Q/r^2 signed by which side the
    source is on.
    """
    q = labelled(statement, "$q") * MICRO
    q1 = labelled(statement, "$Q_1") * MICRO
    q2 = labelled(statement, "$Q_2") * MICRO

    # Positions come from the tikz markers: \draw[...] (x,y) circle ... {$q$}
    positions = {}
    for x, y, name in re.findall(
        r"\\draw\[black,fill\]\s*\(" + _NUM + r"," + _NUM + r"\)\s*circle[^;]*?\{\$([^$]+)\$\}",
        statement,
    ):
        positions[name] = (float(x), float(y))

    x_q = positions["q"][0]
    field = 0.0
    for name, charge in (("Q_1", q1), ("Q_2", q2)):
        x_source = positions[name][0]
        separation = abs(x_q - x_source)
        field += K_COULOMB * charge / separation**2 * math.copysign(1.0, x_q - x_source)

    return [
        ("Ex", field, r"\newton/\coulomb"),
        ("Fx", q * field, r"\newton"),
    ]


def solve_vibrating_string(statement: str) -> list[Answer]:
    """Standing waves on a string fixed at both ends.

    The nth mode fits n half-wavelengths into L, so lambda_n = 2L/n, and with
    v = sqrt(T/mu) that gives f_n = n*v/(2L). The statement asks for the
    frequencies *and* wavelengths of the first N modes, so 2N answers are
    expected, paired mode by mode.
    """
    # The in-class variant prints L twice -- once as the figure's dimension
    # label and once in the body text -- so take the first rather than unpacking.
    length = by_unit(statement, r"\meter")[0]
    mu = by_unit(statement, r"\kilogram/\meter")[0]
    tension = by_unit(statement, r"\newton")[0]
    modes = int(re.search(r"first \$\{?(\d+)\}?\$ vibration modes", statement).group(1))

    speed = math.sqrt(tension / mu)
    answers: list[Answer] = []
    for n in range(1, modes + 1):
        answers.append((f"f{n}", n * speed / (2 * length), r"\hertz"))
        answers.append((f"lambda{n}", 2 * length / n, r"\meter"))
    return answers


# --- CO4c spring questions -------------------------------------------------
# Theta is measured from the vertical in diagram-springs.png, so two springs
# share the weight as 2*k*x*cos(theta) = m*g.
G = 9.81


def solve_spring_constant(statement: str) -> list[Answer]:
    mass, stretch, accel = (
        by_unit(statement, r"\kilogram")[0],
        by_unit(statement, r"\meter")[0],
        by_unit(statement, r"\meter\per\second\squared")[0],
    )
    return [("k", mass * accel / stretch, r"\newton\per\meter")]


def solve_mass_from_k(statement: str) -> list[Answer]:
    k, stretch, accel = (
        by_unit(statement, r"\newton\per\meter")[0],
        by_unit(statement, r"\meter")[0],
        by_unit(statement, r"\meter\per\second\squared")[0],
    )
    return [("m", k * stretch / accel, r"\kilogram")]


def _angle(statement: str) -> float:
    return math.radians(int(re.search(r"\\ang\{(\d+)\}", statement).group(1)))


def solve_hanging_stretch(statement: str) -> list[Answer]:
    k = by_unit(statement, r"\newton\per\meter")[0]
    mass = by_unit(statement, r"\kilogram")[0]
    return [("x", mass * G / (2 * k * math.cos(_angle(statement))), r"\meter")]


def solve_hanging_mass(statement: str) -> list[Answer]:
    k = by_unit(statement, r"\newton\per\meter")[0]
    stretch = by_unit(statement, r"\meter")[0]
    return [
        ("m", 2 * k * stretch * math.cos(_angle(statement)) / G, r"\kilogram")
    ]


def solve_template_series_pair(statement: str) -> list[Answer]:
    """The placeholder circuit in assessment-template.tex.

    R1 and R2 in series across an ideal battery, so one current flows through
    both and each resistor takes its share of the emf.  Verifying the template
    means a document copied from it starts out checked; change the physics
    without writing a solver and this test fails, which is the intended prompt.
    """
    vb = labelled(statement, "$V_b")
    r1 = labelled(statement, "$R_1")
    r2 = labelled(statement, "$R_2")

    current = vb / (r1 + r2)
    return [
        ("I", current, r"\ampere"),
        ("V1", current * r1, r"\volt"),
        ("V2", current * r2, r"\volt"),
    ]


# --- CO1b calculus-of-motion questions -------------------------------------

_MINUTE_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def solve_rocket_burn(statement: str) -> list[Answer]:
    """Straight-line launch from rest, acceleration taken as constant.

    Constant acceleration means a = dv/dt = (v - 0)/T over the burn, and the
    height is the area under v(t) = a t, i.e. a T^2 / 2.  The burn time is
    spelled out in words on the paper ("the first two minutes"), so read it from
    there rather than assuming two.
    """
    match = re.search(
        r"able to reach \$\\SI\{" + _NUM + r"\}\{\\meter\\per\\second\}", statement
    )
    if match is None:
        raise LookupError("no burnout speed in statement")
    speed = float(match.group(1))

    word = re.search(r"first (\w+) minutes", statement)
    if word is None or word.group(1) not in _MINUTE_WORDS:
        raise LookupError("no burn time in statement")
    burn = _MINUTE_WORDS[word.group(1)] * 60.0

    accel = speed / burn
    return [
        ("a_avg", accel, r"\meter\per\second\squared"),
        ("h", accel * burn**2 / 2.0, r"\meter"),
    ]


def solve_particle_position(statement: str) -> list[Answer]:
    """Particle on the x axis with x(t) = A t - B t^3.

    Differentiating, v = A - 3B t^2 and a = -6B t.  The velocity vanishes at
    t = sqrt(A/(3B)), where the acceleration has magnitude 6B sqrt(A/(3B)); at
    the instant the second part names it is simply -6B t.
    """
    match = re.search(
        r"x = \(" + _NUM + r"\\,t\s*-\s*" + _NUM + r"\\,t\^\{3\}\)", statement
    )
    if match is None:
        raise LookupError("no position expression in statement")
    a_coeff, b_coeff = float(match.group(1)), float(match.group(2))

    at_time = re.search(
        r"acceleration of the particle at\s*\$t = \\SI\{" + _NUM + r"\}\{\\second\}",
        statement,
    )
    if at_time is None:
        raise LookupError("no evaluation time in statement")
    t_eval = float(at_time.group(1))

    t_rest = math.sqrt(a_coeff / (3.0 * b_coeff))
    return [
        ("|a| where v=0", 6.0 * b_coeff * t_rest, r"\meter\per\second\squared"),
        ("a(t)", -6.0 * b_coeff * t_eval, r"\meter\per\second\squared"),
    ]


# ---------------------------------------------------------------------------
# Question registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuestionType:
    name: str
    #: Marks where this question's statement begins in the printed output.
    marker: str
    #: Distinguishes this type once a segment has been cut out.
    recognises: Callable[[str], bool]
    #: None for discussion questions, which produce no answer-key entry.
    solve: Callable[[str], list[Answer]] | None


QUESTION_TYPES: tuple[QuestionType, ...] = (
    QuestionType(
        "switch-setting (discussion)",
        r"\textbf{Given the following values}",
        lambda s: "how the switches should be set" in s,
        None,
    ),
    QuestionType(
        "series/parallel three resistors",
        r"\textbf{Given the following values}",
        lambda s: "current in each branch" in s and "$V_b" not in s,
        solve_series_parallel_3r,
    ),
    QuestionType(
        "two batteries, three branches",
        r"\textbf{Given the following values}",
        lambda s: "current in each branch" in s and "$V_b" in s,
        solve_two_battery_three_branch,
    ),
    QuestionType(
        "ladder equivalent resistance",
        r"\textbf{Given the following values}",
        lambda s: "equivalent resistance between points A and B" in s,
        solve_ladder_resistance,
    ),
    QuestionType(
        "three parallel, two series",
        r"\textbf{Given the following values}",
        lambda s: "$R_5" in s,
        solve_three_parallel_two_series,
    ),
    QuestionType(
        "series pair in parallel, power",
        r"\textbf{Given the following values}",
        lambda s: "power dissipated by" in s,
        solve_series_pair_power,
    ),
    QuestionType(
        "series pair in parallel, power (emf wording)",
        "The ideal battery has an emf",
        lambda s: "power dissipated by" in s,
        solve_series_pair_power,
    ),
    QuestionType(
        "capacitor network",
        r"\textbf{Given the following values}",
        lambda s: "charge on each capacitor" in s,
        solve_capacitor_network,
    ),
    QuestionType(
        "capacitor equivalent",
        r"\textbf{Given the following values}",
        lambda s: "$C_7" in s,
        solve_capacitor_equivalent,
    ),
    QuestionType(
        "incandescent bulbs on a breaker",
        "Before the availability of",
        lambda s: "light bulbs" in s,
        solve_light_bulbs,
    ),
    QuestionType(
        "thermal energy claim (discussion)",
        "Students in a PHYS 202 class",
        lambda s: "agree or disagree" in s,
        None,
    ),
    QuestionType(
        "electric field on a line",
        r"\textbf{Charges}",
        lambda s: "$Q_2" in s,
        solve_efield_1d,
    ),
    QuestionType(
        "vibrating string",
        "A student sets up a vibrating string",
        lambda s: "vibration modes" in s,
        solve_vibrating_string,
    ),
    QuestionType(
        "vibrating string (with figure)",
        "The diagram below shows a standing wave",
        lambda s: "vibration modes" in s,
        solve_vibrating_string,
    ),
    QuestionType(
        "spring constant on a surface",
        "An object attached to an ideal massless spring",
        lambda s: "what is the spring constant?" in s,
        solve_spring_constant,
    ),
    QuestionType(
        "mass from spring constant",
        "An object attached to an ideal massless spring",
        lambda s: "mass of the object?" in s,
        solve_mass_from_k,
    ),
    QuestionType(
        "hanging mass, find stretch",
        "Two identical springs",
        lambda s: "How much has one of the springs" in s,
        solve_hanging_stretch,
    ),
    QuestionType(
        "hanging mass, find mass",
        "Two identical springs",
        lambda s: "What is the mass of the object?" in s,
        solve_hanging_mass,
    ),
    QuestionType(
        "template series pair",
        r"\textbf{Given}:",
        lambda s: "determine the current through the circuit" in s,
        solve_template_series_pair,
    ),
    QuestionType(
        "rocket burn, average acceleration and height",
        "The Artemis rocket is estimated",
        lambda s: "average acceleration of the rocket" in s,
        solve_rocket_burn,
    ),
    QuestionType(
        "particle position polynomial",
        r"A particle moving along the $x$ axis",
        lambda s: "position given by" in s,
        solve_particle_position,
    ),
)

_MARKERS = tuple(dict.fromkeys(qt.marker for qt in QUESTION_TYPES))
_MARKER_RE = re.compile("|".join(re.escape(m) for m in _MARKERS))


def split_questions(text: str) -> list[str]:
    """Cut the printed output into one segment per problem statement."""
    starts = [m.start() for m in _MARKER_RE.finditer(text)]
    if not starts:
        return []
    bounds = starts + [len(text)]
    return [text[bounds[i] : bounds[i + 1]] for i in range(len(starts))]


def classify(statement: str) -> QuestionType | None:
    for question_type in QUESTION_TYPES:
        if question_type.marker in statement and question_type.recognises(statement):
            return question_type
    return None
