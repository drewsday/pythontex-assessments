"""Shared fixtures for the assessment test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from known_defects import reason_for  # noqa: E402
from pytexlib import (  # noqa: E402
    doc_id,
    documents_with_code,
    run_document,
)

# How many seeds each property is checked against.
#
# Seeds are fixed integers (0, 1, 2, ...), so results are reproducible rather
# than flaky.  The count still matters: some defects only surface for particular
# parameter coincidences, and the rarest one currently tracked -- a degenerate
# zero answer in KirchoffRules1 -- first appears at seed 75.  Keep this above
# that so every known defect fires deterministically and strict xfail stays
# meaningful.  Raise it locally when hunting something rarer.
SEED_COUNT = 100
SEEDS = list(range(SEED_COUNT))


def pytest_addoption(parser):
    parser.addoption(
        "--seeds",
        type=int,
        default=None,
        help="number of seeds to check each property against (default: 60)",
    )


@pytest.fixture(scope="session")
def seeds(pytestconfig) -> list[int]:
    count = pytestconfig.getoption("--seeds") or SEED_COUNT
    return list(range(count))


def pytest_generate_tests(metafunc):
    """Parametrise any test asking for `document` over every document with code."""
    if "document" in metafunc.fixturenames:
        docs = documents_with_code()
        metafunc.parametrize("document", docs, ids=[doc_id(d) for d in docs])


@pytest.fixture
def check_known(request, document):
    """Mark the running test xfail if `document` has a recorded defect for it.

    Call as `check_known("si_arity")` at the point the property is about to be
    asserted, so a document that is broken for a known reason does not fail the
    build but is still reported.
    """

    def _check(check_name: str):
        reason = reason_for(doc_id(document), check_name)
        if not reason:
            return
        # Strict xfail turns a fixed defect into a visible failure, which is how
        # entries get retired from the registry.  It is only meaningful when the
        # run covers enough seeds to reach the defect: below the default some
        # known defects never fire and every one of them would report XPASS.
        requested = request.config.getoption("--seeds") or SEED_COUNT
        request.node.add_marker(
            pytest.mark.xfail(reason=reason, strict=requested >= SEED_COUNT)
        )

    return _check


@pytest.fixture(scope="session")
def runs_cache():
    """Memoise document runs; several modules ask for the same (doc, seed)."""
    cache: dict[tuple[str, int], object] = {}

    def _run(document: Path, seed: int):
        key = (str(document), seed)
        if key not in cache:
            cache[key] = run_document(document, seed)
        return cache[key]

    return _run
