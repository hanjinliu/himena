from pathlib import Path
import sys
from himena.utils.misc import is_subtype
import pytest

@pytest.mark.parametrize(
    "input_type, super_type, expected",
    [
        ("text", "text", True),
        ("text.something", "text", True),
        ("text", "text.something", False),
        ("text.something", "text.something", True),
        ("text.something", "text.other", False),
        ("a.b.c.d", "a.b.c", True),
    ],
)
def test_is_subtype(input_type, super_type, expected):
    assert is_subtype(input_type, super_type) == expected

def test_cli_args():
    from himena.utils import cli

    assert cli.to_command_args("rsync", "src", "dst") == ["rsync", "-a", "--progress", "src", "dst"]
    assert cli.to_command_args("rsync", "src", "dst", is_dir=True) == ["rsync", "-ar", "--progress", "src", "dst"]
    assert cli.to_command_args("scp", "src", "dst") == ["scp", "src", "dst"]
    assert cli.to_command_args("scp", "src", "dst", is_dir=True) == ["scp", "-r", "src", "dst"]

    if sys.platform == "win32":
        assert cli.to_wsl_path(Path("C:/Users/username")) == "/mnt/c/Users/username"
        assert cli.to_wsl_path(Path("C:/Users/username/")) == "/mnt/c/Users/username"
        assert cli.to_wsl_path(Path("C:/")) == "/mnt/c"
        assert cli.to_wsl_path(Path("C:/Program Files/")) == "/mnt/c/Program Files"
        assert cli.to_wsl_path(Path("D:/")) == "/mnt/d"

    assert cli.local_to_remote("rsync", Path("C:/src"), "dst") == ["rsync", "-a", "--progress", "C:/src", "dst"]
    assert cli.local_to_remote("rsync", Path("C:/src"), "dst", is_dir=True) == ["rsync", "-ar", "--progress", "C:/src", "dst"]
    if sys.platform == "win32":
        assert cli.local_to_remote("rsync", Path("C:/src"), "~/dst", is_wsl=True) == ["wsl", "-e", "rsync", "-a", "--progress", "/mnt/c/src", "~/dst"]

    assert cli.local_to_remote("scp", Path("C:/src"), "dst") == ["scp", "C:/src", "dst"]
    assert cli.local_to_remote("scp", Path("C:/src"), "dst", is_dir=True) == ["scp", "-r", "C:/src", "dst"]
    if sys.platform == "win32":
        assert cli.local_to_remote("scp", Path("C:/src"), "~/dst", is_wsl=True) == ["wsl", "-e", "scp", "/mnt/c/src", "~/dst"]

    assert cli.remote_to_local("rsync", "src", Path("dst")) == ["rsync", "-a", "--progress", "src", "dst"]
    assert cli.remote_to_local("rsync", "src", Path("dst"), is_dir=True) == ["rsync", "-ar", "--progress", "src", "dst"]
    if sys.platform == "win32":
        assert cli.remote_to_local("rsync", "~/src", Path("C:/dst"), is_wsl=True) == ["wsl", "-e", "rsync", "-a", "--progress", "~/src", "/mnt/c/dst"]

    assert cli.remote_to_local("scp", "src", Path("dst")) == ["scp", "src", "dst"]
    assert cli.remote_to_local("scp", "src", Path("dst"), is_dir=True) == ["scp", "-r", "src", "dst"]
    if sys.platform == "win32":
        assert cli.remote_to_local("scp", "~/src", Path("C:/dst"), is_wsl=True) == ["wsl", "-e", "scp", "~/src", "/mnt/c/dst"]

def test_submodule():
    from himena.utils.entries import is_submodule

    assert is_submodule("himena_builtins.io", "himena_builtins")
    assert is_submodule("himena_builtins.io", "himena_builtins.io")
    assert not is_submodule("himena_builtins.io", "himena_test_plugin.io")
