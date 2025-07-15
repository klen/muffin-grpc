import shutil
from pathlib import Path

import pytest

SRC_DIR = Path("tests/proto/src")
BUILD_DIR = Path("tests/proto/compiled")


@pytest.fixture(scope="session")
def aiolib():
    return "asyncio", {"use_uvloop": False}


@pytest.fixture(autouse=True)
async def clean_build():
    if BUILD_DIR.exists():
        for path in BUILD_DIR.glob("**/*"):
            if path.is_file() and path.suffix in {".py", ".pyc"}:
                path.unlink()
            if path.name == "__pycache__":
                shutil.rmtree(path)


@pytest.fixture
def app():
    from muffin import Application

    return Application()
