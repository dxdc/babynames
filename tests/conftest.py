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


@pytest.fixture(scope="module")
def forced_merges_path():
    return FIXTURES / "forced_merges.csv"


@pytest.fixture(scope="module")
def nicknames_path():
    return FIXTURES / "nicknames.csv"


@pytest.fixture(scope="module")
def pronunciation_overrides_path():
    return FIXTURES / "pronunciation_overrides.csv"


@pytest.fixture(scope="module")
def territory_dir():
    return FIXTURES / "territories"
