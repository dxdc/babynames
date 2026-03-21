from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES


@pytest.fixture
def ssa_dir():
    return FIXTURES / "babynames"


@pytest.fixture
def biblical_path():
    return FIXTURES / "biblical_names.csv"
