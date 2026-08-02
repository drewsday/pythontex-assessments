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
| `test_physics.py` | Answer keys match an independent recomputation, in value and unit |

(`physics.py` is not a test module — it holds the solvers `test_physics.py` uses.)

## Known defects

`tests/known_defects.py` records the problems that exist today. Tests consult it
and mark those cases `xfail` instead of failing, so the suite runs green and is
adoptable immediately while still tracking every problem.

The xfails are **strict**: when a defect is fixed the test reports `XPASS` and
the build goes red, which is the signal to delete the entry. That is intentional
— it stops the registry from quietly accumulating entries that no longer apply.

Do not add to the registry to silence a *new* failure. A new failure is a
regression and belongs fixed at the source.

## Physics checking

`physics.py` holds the solvers, one per *kind* of question rather than per
document, because the assessments compose the same handful of problems —
`CO10-CO11-CO12.tex` is `DC_Circuits1` followed by `EquivalentResistance1`
followed by `KirchoffRules1`, and three documents share the same
power-dissipation circuit. Keying by question type means each derivation is
written once.

`test_physics.py` walks each document, cuts its printed output into problem
statements, matches each to a question type, and compares the recomputed answers
against what randassign recorded — checking **units as well as magnitudes**,
since a right number under the wrong unit is still a wrong answer.

Every answer key in the repository is covered.

### Adding an assessment

Add a solver to `physics.py` and register it in `QUESTION_TYPES` with a `marker`
(text that begins the statement) and a `recognises` predicate. Re-derive the
physics from the circuit or figure — copying the document's own expression makes
the test assert only that the code equals itself.

`test_every_document_with_a_key_is_checked` fails if a keyed document prints a
question no type recognises, so a new assessment cannot land unverified.

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
