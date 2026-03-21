from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def fixtures_dir():
    return FIXTURES


@pytest.fixture(scope="module")
def ssa_dir():
    return FIXTURES / "babynames"


@pytest.fixture(scope="module")
def biblical_path():
    return FIXTURES / "biblical_names.csv"
