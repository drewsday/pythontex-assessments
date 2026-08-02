"""The randomisation actually has to randomise.

Both failures here are silent: the document builds, the pages look right, and
every student gets the same question.
"""

from __future__ import annotations

import ast

from pytexlib import extract_blocks


def _choice_calls(source: str):
    """Yield every `random.choice([...])` literal list found in `source`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:  # covered by the smoke test
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name != "choice" or not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, (ast.List, ast.Tuple)):
            yield node, arg


def test_no_dead_choices(document, check_known):
    """`random.choice` over identical options is unfinished randomisation."""
    check_known("no_dead_choices")

    offenders = []
    for block_index, source in enumerate(extract_blocks(document)):
        for node, arg in _choice_calls(source):
            literals = [e.value for e in arg.elts if isinstance(e, ast.Constant)]
            if len(literals) != len(arg.elts) or len(literals) < 2:
                continue  # not all literal, or a genuine single-item list
            if len(set(literals)) == 1:
                offenders.append(
                    f"block {block_index}, line {node.lineno}: "
                    f"{len(literals)} copies of {literals[0]!r}"
                )

    assert not offenders, "random.choice with no choice:\n  " + "\n  ".join(offenders)


def test_output_varies_across_seeds(document, seeds, runs_cache, check_known):
    """A document that draws random values should not print the same page twice."""
    sources = "\n".join(extract_blocks(document))
    draws_randomly = any(
        token in sources
        for token in ("random.choice", "random.uniform", "random.randrange",
                      "random.randint", "uniform(", "randrange(", "randint(")
    )
    if not draws_randomly:
        return  # static documents are legitimately identical every run
    if "print(" not in sources:
        # Values reach the page through inline \py{...} macros, so variation is
        # not observable from stdout.
        return
    check_known("varies_across_seeds")

    outputs = {runs_cache(document, seed).text for seed in seeds}
    assert len(outputs) > 1, (
        f"document draws random values but produced identical output on all "
        f"{len(seeds)} seeds"
    )
