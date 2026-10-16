import pytest

from app.services.search.engine import search_engine
from app.services.search.seed_data import load_seed_documents


@pytest.fixture(scope="session", autouse=True)
def build_index():
    search_engine.build(load_seed_documents())
