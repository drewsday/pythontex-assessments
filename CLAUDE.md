# Working in this repository

Randomized physics assessments for PHYS 110/201/202, written in LaTeX with
[PythonTeX](https://github.com/gpoore/pythontex) and
[randassign](https://github.com/gpoore/randassign).

## The shape of the code

There is no importable Python package. **Everything that randomizes problems and
computes answer keys lives inside `\begin{pycode} ... \end{pycode}` blocks in the
`.tex` files.** 27 documents, 21 with code, 15 recording an answer key.

Two things follow that are easy to get wrong:

- PythonTeX runs all of a document's blocks in **one interpreter session**, so
  they share a namespace. A name defined in block 1 is visible in block 3.
  Running a block in isolation reports `NameError`s that never happen in a real
  build.
- randassign writes the answer key to a **separate file**, as a side effect. It
  is never passed to `pdflatex` by anything here. A key can therefore contain
  LaTeX that would not compile, and nothing will notice except the tests.

## Layout

```
*.tex                    the assessments; flat, no subdirectories
Picture1.jpg             figures included by documents
diagram-springs.png
testing-pythontex.ipynb  scratch notebook, not part of the build
tests/                   the suite (below)
requirements-dev.txt     test deps only; randassign is deliberately absent
pytest.ini               testpaths=tests, -ra --strict-markers
.github/workflows/tests.yml
```

`tests/` splits into three support modules and eight test modules:

| Module | Role |
|---|---|
| `pytexlib.py` | Extracts `pycode`/`pyblock` blocks, runs a document under a seed with a `randassign` stub, and inspects the generated LaTeX (`si_arity_errors`, `unbalanced_braces`, `unfilled_placeholders`, `si_quantities`) |
| `conftest.py` | `SEED_COUNT = 100`; parametrises any test taking `document` over every document with code; provides `seeds`, `runs_cache`, `check_known` |
| `known_defects.py` | The `(document, check) -> reason` registry |
| `test_smoke.py` | Every block compiles, runs on every seed, and prints something |
| `test_latex_output.py` | Generated LaTeX will typeset: `\SI` arity, brace balance, no unsubstituted `{0:.3g}` |
| `test_answer_key.py` | Keys are non-empty formatted LaTeX, finite, and not degenerate |
| `test_consistency.py` | Every symbol given a value labels exactly one element in the figure; no two `.tex` files are byte-identical |
| `test_randomization.py` | No `random.choice` over identical options; output varies across seeds |
| `test_determinism.py` | The same seed reproduces the same paper and the same key |
| `test_document_shape.py` | CO4c emits complete copy-major assessments, numbered from 1 |
| `test_physics.py` | Answer keys match an independent recomputation, in value and unit |

`physics.py` is not a test module — it holds the solvers `test_physics.py` uses.

## Commands

```bash
# Tests (no TeX installation needed - runs the pycode blocks directly)
pip install -r requirements-dev.txt
python -m pytest tests/

# Build one assessment. All three passes are required: pdflatex emits the code,
# pythontex runs it, pdflatex pulls the output back in.
pdflatex -interaction=nonstopmode Assessment.tex
pythontex Assessment.tex
pdflatex -interaction=nonstopmode Assessment.tex
```

Green as of the last commit: **329 passed, 10 skipped, 5 xfailed**, in about 5
seconds. The skips are seven physics cases with no key to check (six record
none, one emits no problem statement and has its own test) and three smoke
cases that emit via inline `\py{...}` rather than `print()`; the xfails are the
five entries in `known_defects.py`.

Every property is checked against fixed seeds (0, 1, 2, …), so runs are
reproducible rather than flaky. `--seeds=N` widens the search when hunting
something rare. Lowering it below the default of 100 weakens the suite — the
degenerate answer in `KirchoffRules1` first appears at seed 75, so strict xfail
is relaxed automatically when you ask for fewer. See `tests/README.md`.

## Known defects and the ratchet

`tests/known_defects.py` records defects that exist today. Tests consult it and
mark those cases `xfail`, so the suite runs green while still tracking every
problem.

**The xfails are strict.** Fixing a defect turns its test into `XPASS`, which
fails the build — that is the signal to delete the entry. When a fix causes an
XPASS, remove the registry entry in the same commit.

Never add to the registry to silence a *new* failure. A new failure is a
regression and belongs fixed at the source.

A registry key is `(document filename, check name)`. The check name is the
string the test passes to `check_known(...)`, not the test function name. The
full set in use:

```
si_arity  brace_balance  unfilled_placeholders
key_not_empty  solution_types  finite_answers  no_degenerate_answers
symbols_match_diagram  no_dead_choices  varies_across_seeds
determinism_text  determinism_key  physics
```

## Verifying a change

Passing tests do not prove a check works. Before claiming a checker is correct,
**mutate the source it checks and confirm the mutation is caught.** Several bugs
in this suite were found that way.

One trap: if a document is already `xfail`, strict xfail masks the pytest-level
signal — a mutated document still fails and reports XFAIL, not a failure. Verify
those solvers directly instead, by mutating a value that currently *passes*.

## Physics checks

`tests/physics.py` holds solvers keyed by **question type**, not by document,
because the assessments compose the same handful of problems —
`CO10-CO11-CO12.tex` is `DC_Circuits1` + `EquivalentResistance1` +
`KirchoffRules1` concatenated, and three documents share one power-dissipation
circuit. Keying by type means each derivation is written once.

`test_physics.py` cuts each document's printed output into problem statements
with `split_questions`, matches each to a `QuestionType` via `classify`, and
compares the recomputed answers against what randassign recorded.

To cover a new assessment: write a solver returning `list[Answer]` and register
it in `QUESTION_TYPES` with a `marker` (text that begins the statement) and a
`recognises` predicate. `test_every_document_with_a_key_is_checked` fails if a
keyed document prints a question no type recognises, so a new assessment cannot
land unverified.

Re-derive the physics from the circuit or figure. Copying the document's own
expression makes the test assert only that the code equals itself.

Answers are checked in **unit as well as magnitude**. A right number under the
wrong unit is still a wrong answer, and has reached students here more than once.

## Traps that have already cost time

- **`from pylab import *` shadows `uniform`** with `numpy.random.uniform`, while
  `randrange` stays on the standard-library generator. `random.seed()` then
  drives only one of the two streams and the document silently stops being
  reproducible. Prefer `import random` and `random.uniform`. Thirteen documents
  still star-import pylab; that is fine, because none of them call a numpy RNG
  function. `test_determinism.py` is the check that matters, not the import.
- **`pythontex` is not on PyPI.** It ships with TeX Live. On Ubuntu the package
  is `texlive-extra-utils`, which provides `/usr/bin/pythontex`, `pythontex.py`
  **and** `pythontex.sty` — not `texlive-latex-extra`.
- **`\SI` takes two arguments**, a value and a unit. For a dimensionless answer
  use `\num`. Not every document loads siunitx: `simple_example.tex` writes
  units as literal `~cm`.
- **Not every `.tex` file is a document.** `attempt.tex` and `name.tex` are
  one-line `\input` fragments. Select documents with
  `grep -l '\documentclass'`.
- **Not every document contains Python.** Six of the 27 are plain LaTeX
  (`CapacitorCircuits1`, `CircuitikzExamples`, `Test`,
  `coupled-oscillators-still-testing`, `test-pattern2`, `test-pattern3`);
  running `pythontex` on them fails with "Code file does not exist", which says
  nothing about whether they are valid. The build job skips that pass when no
  `.pytxcode` was produced.
- **`addsoln` is sometimes commented out.** Four documents reference it but
  record no key. Detect real calls with the AST-based `calls_addsoln` in
  `tests/pytexlib.py`, not a substring search.
- **Duplicate documents are banned.** The repository once carried two
  byte-identical pairs, so every defect had to be recorded twice and a fix to
  one copy silently left the other broken.
  `test_consistency.py::test_no_duplicate_documents` guards against reintroducing
  them; copy-and-edit a document, do not copy it verbatim.

## CI

`.github/workflows/tests.yml` has two gating jobs: `assessment logic` runs the
test suite on Python 3.11, and `pdflatex build` typesets every document found by
`grep -l '\documentclass'` through the full three-pass cycle. The build job
covers the assessments, **not** the answer keys — those are only checked by
`tests/test_latex_output.py`.

Two details in that job are load-bearing: it preflights every `.cls`/`.sty` with
`kpsewhich` so a missing package is reported once instead of costing a CI round
trip, and it passes `--interpreter python:python3` because Ubuntu ships no bare
`python`, which is pythontex's default.

## Open work

Five defects remain in `known_defects.py`. Each needs a pedagogical decision from
the instructor before it can be fixed, not just a code change: whether `V_a` and
`V_b` should be drawn from ranges that cannot coincide (`KirchoffRules1`, and
`CO10-CO11-CO12` which embeds it), whether `R_D` should always appear in
`KirchoffRules2`'s circuit, and which alternatives the dead `random.choice` calls
in `PowerInDCCircuits1`/`PowerInDCCircuits2` were meant to offer. Ask rather than
guess.

Separately, four documents record no answer key at all
(`CO6-PHYS201-v1{,-stripped_down}.tex`, `DC_Circuits2.tex`,
`KirchoffRules2.tex`). Writing those is ordinary work — derive from the circuit,
add a solver to `physics.py` — but settle `KirchoffRules2`'s `R_D` question
first, since there is no point writing a key for a malformed problem.
