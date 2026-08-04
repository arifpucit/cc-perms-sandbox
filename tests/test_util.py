import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.util import add


def test_add():
    assert add(2, 3) == 5
