"""Helpers for exercising the Python embedded in the PythonTeX assessments.

There is no importable Python package in this repository: all of the code that
randomises problems and computes answer keys lives inside ``\\begin{pycode}``
blocks in the ``.tex`` files.  This module pulls those blocks out and runs them
the way PythonTeX does, so they can be tested like ordinary code.
"""

from __future__ import annotations

import contextlib
import io
import math
import re
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Matplotlib must be headless: several documents do `from pylab import *`.
try:  # pragma: no cover - import side effect only
    import matplotlib

    matplotlib.use("Agg")
except ImportError:  # pragma: no cover
    pass


# ---------------------------------------------------------------------------
# randassign stub
# ---------------------------------------------------------------------------
# The real randassign writes solution files as a side effect of a pythontex run.
# For tests we only care about what gets handed to addsoln(), so a stub keeps
# the suite hermetic and free of filesystem side effects.

_COLLECTED: list = []


class _StubRandAssign:
    def __init__(self, *args, **kwargs):
        pass

    def addsoln(self, soln):
        _COLLECTED.append(soln)


def _install_randassign_stub() -> None:
    module = types.ModuleType("randassign")
    module.RandAssign = _StubRandAssign
    sys.modules["randassign"] = module


_install_randassign_stub()


# ---------------------------------------------------------------------------
# Block extraction
# ---------------------------------------------------------------------------

# Only executable environments.  `pysub` holds LaTeX for substitution, not code.
_BLOCK_RE = re.compile(
    r"\\begin\{py(?:code|block)\}(.*?)\\end\{py(?:code|block)\}", re.DOTALL
)


def tex_files() -> list[Path]:
    """Every .tex file in the repository, sorted for stable test ids."""
    return sorted(
        set(REPO_ROOT.glob("*.tex")) | set(REPO_ROOT.glob("*/*.tex")),
        key=lambda p: str(p.relative_to(REPO_ROOT)),
    )


def extract_blocks(path: Path) -> list[str]:
    """Return the source of each executable PythonTeX block in `path`."""
    return _BLOCK_RE.findall(path.read_text(encoding="utf-8", errors="replace"))


def documents_with_code() -> list[Path]:
    return [p for p in tex_files() if extract_blocks(p)]


def doc_id(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def calls_addsoln(path: Path) -> bool:
    """True if the document really calls addsoln, ignoring commented-out ones.

    Several documents carry a commented `ra.addsoln(...)` left over from an
    earlier draft, so a substring search would claim they record an answer key
    when they record nothing.
    """
    import ast

    for source in extract_blocks(path):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "addsoln"
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """What one document produced for one seed."""

    path: Path
    seed: int
    text: str = ""
    solutions: list = field(default_factory=list)

    @property
    def flat_solutions(self) -> list[str]:
        """Solutions as a flat list of strings.

        addsoln() is called with a string in most documents, with a list in
        others, so normalise before asserting on content.
        """
        out: list[str] = []
        for soln in self.solutions:
            if isinstance(soln, (list, tuple)):
                out.extend(str(x) for x in soln)
            else:
                out.append(str(soln))
        return out


def run_document(path: Path, seed: int) -> RunResult:
    """Execute every block in `path` and capture its output.

    PythonTeX runs all of a document's blocks in one interpreter session, so the
    blocks share a single namespace here too; running them in isolation would
    report NameErrors that do not happen in a real build.
    """
    import random

    random.seed(seed)
    _COLLECTED.clear()

    namespace: dict = {"__name__": "__main__"}
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        for index, source in enumerate(extract_blocks(path)):
            code = compile(source, f"{doc_id(path)}#block{index}", "exec")
            exec(code, namespace)  # noqa: S102 - executing the code is the point

    return RunResult(
        path=path, seed=seed, text=buffer.getvalue(), solutions=list(_COLLECTED)
    )


# ---------------------------------------------------------------------------
# LaTeX inspection
# ---------------------------------------------------------------------------

_SI_RE = re.compile(r"\\SI(?![a-zA-Z])")


def _read_group(text: str, index: int) -> int | None:
    """If a brace group starts at `index`, return the index just past it."""
    while index < len(text) and text[index] in " \t\n":
        index += 1
    if index >= len(text) or text[index] != "{":
        return None
    depth = 0
    while index < len(text):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return None  # unterminated


def si_arity_errors(text: str) -> list[str]:
    r"""Find `\SI` calls that are not followed by exactly two brace groups.

    `\SI{value}{unit}` needs both arguments; emitting `\SI{24} light bulbs`
    is a hard LaTeX error that only shows up when the document is typeset.
    """
    errors = []
    for match in _SI_RE.finditer(text):
        index = match.end()
        for _ in range(2):
            nxt = _read_group(text, index)
            if nxt is None:
                errors.append(re.sub(r"\s+", " ", text[match.start() : match.start() + 60]))
                break
            index = nxt
    return errors


def unbalanced_braces(text: str) -> int:
    """Return the net brace depth; nonzero means the output cannot typeset.

    Escaped braces (\\{ and \\}) are not grouping characters and are skipped.
    """
    depth = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return depth


# `{0}` / `{2:.3g}` surviving into the output means a .format() call was missed.
_UNFILLED_RE = re.compile(r"\{\d+:[^}]*\}")


def unfilled_placeholders(text: str) -> list[str]:
    """Find str.format placeholders that were never substituted.

    Only placeholders carrying a format spec are reported: a bare `{220}` is
    almost always a legitimately substituted value inside a LaTeX group.
    """
    return _UNFILLED_RE.findall(text)


_SI_VALUE_RE = re.compile(r"\\SI\{(-?\d*\.?\d+(?:[eE][+-]?\d+)?)\}")


def si_values(text: str) -> list[float]:
    r"""Every numeric value appearing as the first argument of an `\SI`."""
    return [float(m) for m in _SI_VALUE_RE.findall(text)]


def si_quantities(text: str) -> list[tuple[float, str]]:
    r"""Every `\SI{value}{unit}` pair in `text`."""
    pattern = re.compile(r"\\SI\{(-?\d*\.?\d+(?:[eE][+-]?\d+)?)\}\{([^{}]*)\}")
    return [(float(v), u) for v, u in pattern.findall(text)]


def is_finite(value: float) -> bool:
    return math.isfinite(value)
