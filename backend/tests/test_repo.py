import pytest

from agentcollab.repo import apply_files, gather_context, make_patch, safe_path
from agentcollab.repo.files import UnsafePath


@pytest.mark.parametrize("bad", ["/etc/passwd", "../x.py", "a/../../x.py", ".git/config", ""])
def test_unsafe_paths_rejected(tmp_path, bad):
    with pytest.raises(UnsafePath):
        safe_path(tmp_path, bad)


def test_context_skips_ignored_dirs_and_big_files(tmp_path):
    (tmp_path / "app.py").write_text("print(1)\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("x")
    (tmp_path / "big.py").write_text("x" * 50_000)
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")
    assert gather_context(tmp_path) == {"app.py": "print(1)\n"}


def test_patch_and_apply(tmp_path):
    old = {"app.py": "a\n"}
    new = {"app.py": "b\n", "pkg/new.py": "c\n"}
    patch = make_patch(old, new)
    assert "-a\n+b" in patch and "+++ b/pkg/new.py" in patch and "/dev/null" in patch
    apply_files(tmp_path, new)
    assert (tmp_path / "pkg" / "new.py").read_text() == "c\n"
