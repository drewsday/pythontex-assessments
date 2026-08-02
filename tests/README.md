# Test suite

These tests exercise the Python embedded in the `.tex` files. There is no
importable package here: everything that randomises problems and computes answer
keys lives inside `\begin{pycode}` blocks, so `tests/pytexlib.py` extracts those
blocks and runs them the way PythonTeX does — one shared namespace per document,
with a stub standing in for `randassign`.

## Running

```
pip install -r requirements-dev.txt
python -m pytest tests/
```

Every property is checked against a fixed range of seeds (0, 1, 2, …), so runs
are reproducible rather than flaky. Use `--seeds=N` to widen the search when
hunting something rare:

```
python -m pytest tests/ --seeds=500
```

Lowering `--seeds` below the default of 100 is supported but weakens the suite:
some known defects only appear at particular seeds — the degenerate answer in
`KirchoffRules1` first shows up at seed 75 — so strict xfail is relaxed
automatically when you ask for fewer.

## What each module covers

| Module | Property |
|---|---|
| `test_smoke.py` | Every block compiles, runs on every seed, and prints something |
| `test_latex_output.py` | Generated LaTeX will typeset: `\SI` arity, brace balance, no unsubstituted `{0:.3g}` |
| `test_answer_key.py` | Keys are non-empty formatted LaTeX, finite, and not degenerate |
| `test_consistency.py` | Every symbol given a value labels exactly one element in the figure |
| `test_randomization.py` | No `random.choice` over identical options; output varies across seeds |
| `test_determinism.py` | The same seed reproduces the same paper and the same key |
| `test_document_shape.py` | CO4c emits complete copy-major assessments, numbered from 1 |
| `test_physics.py` | Answer keys match an independent recomputation |

## Known defects

`tests/known_defects.py` records the problems that exist today. Tests consult it
and mark those cases `xfail` instead of failing, so the suite runs green and is
adoptable immediately while still tracking every problem.

The xfails are **strict**: when a defect is fixed the test reports `XPASS` and
the build goes red, which is the signal to delete the entry. That is intentional
— it stops the registry from quietly accumulating entries that no longer apply.

Do not add to the registry to silence a *new* failure. A new failure is a
regression and belongs fixed at the source.

## Adding an assessment

`test_physics.py::test_every_document_with_a_key_has_a_checker` lists every
document whose answer key has no independent check. It is currently `xfail`,
since most assessments predate the suite. When you add an assessment, write a
checker in `test_physics.py` and register it in `CHECKERS` — re-derive the
physics from the circuit or figure rather than copying the document's own
expression, otherwise the test only asserts that the code equals itself.

## What this suite does not cover

It runs the Python; it does not typeset the LaTeX. Errors that only appear under
`pdflatex` — a missing package, a circuitikz syntax error — are caught by the
`pdflatex build` job in `.github/workflows/tests.yml`, not here.

That job compiles the **assessments**, not the **answer keys**. randassign
writes keys to a separate file as a side effect, and that file is never passed to
pdflatex. `PowerInDCCircuits2.tex` typesets cleanly despite its one-argument
`\SI`, because the defect is in its key. Answer-key LaTeX is checked only by
`test_latex_output.py` here, which is why that test asserts over
`result.text` *and* `result.flat_solutions`.
