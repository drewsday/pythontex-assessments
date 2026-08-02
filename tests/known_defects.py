"""Defects that exist today, recorded so the suite can run green.

Each entry maps ``(document, check)`` to the reason it currently fails.  Tests
consult this registry and mark the case ``xfail`` instead of failing the build,
so the suite is adoptable immediately while still tracking every known problem.

When a defect is fixed the corresponding test reports XPASS, which is the signal
to delete the entry here.  Do not add to this list to silence a *new* failure:
new failures are regressions and should be fixed at the source.
"""

from __future__ import annotations

KNOWN_DEFECTS: dict[tuple[str, str], str] = {
    # Four circuit elements are independently randomised between
    # `resistor=$R_D$` and `short`, but the problem text always states a value
    # for R_D.  Only ~24% of generated problems show R_D exactly once: 5% omit
    # it entirely and 70% put the same label on two or more elements.
    ("KirchoffRules2.tex", "symbols_match_diagram"): (
        "KirchoffRules2.tex:131-134 randomise R_D in and out of the circuit "
        "while the text always gives it a value"
    ),
    # I1 = (Va - Vb) / R1 with Va drawn from [1.5, 3, 4.5, 6] and Vb from
    # [6, 9, 12, 15, 18], so Va - Vb is never positive: ~94% of papers report a
    # negative current and ~6% report exactly zero (both batteries land on 6 V),
    # which makes the problem degenerate.
    ("KirchoffRules1.tex", "no_degenerate_answers"): (
        "KirchoffRules1.tex:122 can yield I1 = 0 when Va == Vb == 6"
    ),
    # CO10-CO11-CO12.tex embeds the same question, so it collapses the same way.
    ("CO10-CO11-CO12.tex", "no_degenerate_answers"): (
        "CO10-CO11-CO12.tex can emit an answer of exactly zero"
    ),
    # `from pylab import *` binds `uniform` to numpy.random.uniform while
    # `randrange` stays on the stdlib generator, so random.seed() drives only one
    # of the two streams and a given paper cannot be regenerated. This is the
    # same defect that was fixed in CO4c-Fall2021-PHYS201.tex; the fix there is
    # to drop the pylab star-import and use random.uniform.
                    # These two draw their randomised values with the numpy generator, so the
    # answer key changes run to run as well as the paper.  The CO6 pair escapes
    # this one only because their addsoln calls are commented out.
            # random.choice over four identical options - unfinished randomisation that
    # looks functional from the outside.
    ("PowerInDCCircuits1.tex", "no_dead_choices"): (
        "PowerInDCCircuits1.tex:111 chooses between four identical options"
    ),
    ("PowerInDCCircuits2.tex", "no_dead_choices"): (
        "PowerInDCCircuits2.tex:196 chooses between four identical options"
    ),
    # Capacitances and charges are computed in farads and coulombs but reported
    # with \micro\farad and \micro\coulomb, so every one is off by a factor of
    # 1e6: a 164 uF equivalent capacitance prints as "0.000164 uF". The
    # voltages and energies in the same key are correct, which is what makes it
    # easy to miss. Fix by dividing by 1e-6 at format time, as the problem
    # statement already does. Same class of error as the kilogram/newton-per-
    # metre mix-up fixed in CO4c-Fall2021-PHYS201.tex.
        # `i = 1; while i < number:` yields number-1 frequencies while the statement
    # asks for "the first {number} vibration modes". The frequencies that are
    # reported are correct; the highest mode is simply missing. The loop bound
    # should be `while i <= number`. The statement also asks for wavelengths,
    # which the key never records at all.
            # addsoln() is handed a bare float rather than formatted LaTeX.
    ("simple_example.tex", "solution_types"): (
        "simple_example.tex passes a float to addsoln instead of a string"
    ),
}


def reason_for(document: str, check: str) -> str | None:
    """Return the known-defect reason for this case, or None if it should pass."""
    return KNOWN_DEFECTS.get((document, check))
