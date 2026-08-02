r"""The generated LaTeX has to typeset.

These catch the failure mode that is invisible until pdflatex runs -- and, since
the answer key is written by randassign rather than printed into the document,
invisible until someone opens the key.
"""

from __future__ import annotations

from pytexlib import si_arity_errors, unbalanced_braces, unfilled_placeholders


def _all_emitted_text(result) -> str:
    """Document body plus answer key: both are LaTeX and both must be valid."""
    return result.text + "\n" + "\n".join(result.flat_solutions)


def test_si_macros_have_two_arguments(document, seeds, runs_cache, check_known):
    r"""\SI{value}{unit} needs both arguments; one argument is a LaTeX error."""
    check_known("si_arity")

    offenders: list[str] = []
    for seed in seeds:
        result = runs_cache(document, seed)
        for bad in si_arity_errors(_all_emitted_text(result)):
            offenders.append(f"seed {seed}: {bad}")

    assert not offenders, "malformed \\SI in {} of {} seeds:\n  {}".format(
        len({o.split(':')[0] for o in offenders}),
        len(seeds),
        "\n  ".join(offenders[:5]),
    )


def test_braces_are_balanced(document, seeds, runs_cache, check_known):
    """Unbalanced braces in generated output break the build at typeset time."""
    check_known("brace_balance")

    offenders = []
    for seed in seeds:
        result = runs_cache(document, seed)
        depth = unbalanced_braces(result.text)
        if depth != 0:
            offenders.append(f"seed {seed}: net brace depth {depth:+d}")

    assert not offenders, "unbalanced braces:\n  " + "\n  ".join(offenders[:5])


def test_no_unfilled_format_placeholders(document, seeds, runs_cache, check_known):
    """A surviving `{0:.3g}` means a .format() call was forgotten."""
    check_known("unfilled_placeholders")

    offenders = []
    for seed in seeds:
        result = runs_cache(document, seed)
        found = unfilled_placeholders(_all_emitted_text(result))
        if found:
            offenders.append(f"seed {seed}: {found[:3]}")

    assert not offenders, "unsubstituted placeholders:\n  " + "\n  ".join(offenders[:5])
