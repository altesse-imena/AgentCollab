import os
import pytest
from uploads import read_upload

@pytest.fixture
def base(tmp_path):
    b = tmp_path / "uploads"
    (b / "sub").mkdir(parents=True)
    (b / "a.txt").write_text("A")
    (b / "sub" / "b.txt").write_text("B")
    (tmp_path / "secret.txt").write_text("S")
    os.symlink(tmp_path / "secret.txt", b / "link.txt")
    return b

def test_reads_files(base):
    assert read_upload(str(base), "a.txt") == "A"
    assert read_upload(str(base), "sub/b.txt") == "B"

@pytest.mark.parametrize("name", ["../secret.txt", "sub/../../secret.txt", "link.txt"])
def test_rejects_escape(base, name):
    with pytest.raises(ValueError):
        read_upload(str(base), name)

def test_rejects_absolute(base, tmp_path):
    with pytest.raises(ValueError):
        read_upload(str(base), str(tmp_path / "secret.txt"))
