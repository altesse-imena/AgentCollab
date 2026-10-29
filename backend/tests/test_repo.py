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


def _big_repo(tmp_path):
    files = {
        "billing/invoice.py": "from billing.tax import rate\n" + "#" * 500,
        "billing/tax.py": "rate = 0.05\n" + "#" * 500,
        "tests/test_invoice.py": "#" * 500,
        "README.md": "#" * 500,
        "unrelated/huge.py": "#" * 5000,
        "unrelated/other.py": "#" * 500,
    }
    for path, body in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(body)
    return tmp_path


def test_small_repo_sent_whole(tmp_path):
    repo = _big_repo(tmp_path)
    assert len(gather_context(repo, "anything")) == 6


def test_over_limit_keeps_relevant_files(tmp_path):
    repo = _big_repo(tmp_path)
    ctx = gather_context(repo, "Fix rounding in invoice.py", max_total_bytes=2_200)
    assert list(ctx) == [
        "billing/invoice.py", "billing/tax.py", "tests/test_invoice.py", "README.md"
    ]  # fmt: skip
