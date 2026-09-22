from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath
import subprocess


def local_to_remote(
    protocol: str,
    src: Path,
    dst: str,
    is_wsl: bool = False,
    is_dir: bool = False,
    port: int = 22,
) -> list[str]:
    """Send local file to the remote host."""
    if is_dir:
        dst = PurePosixPath(dst).parent.as_posix()
    if is_wsl:
        src_wsl = to_wsl_path(src)
        args = ["wsl", "-e"] + to_command_args(
            protocol, src_wsl, dst, is_dir, port=port
        )
    else:
        args = to_command_args(protocol, src.as_posix(), dst, is_dir, port=port)
    return args


def remote_to_local(
    protocol: str,
    src: str,
    dst_path: Path,
    is_wsl: bool = False,
    is_dir: bool = False,
    port: int = 22,
) -> list[str]:
    """Run scp/rsync command to move the file from remote to local `dst_path`."""
    dst_path = dst_path.resolve()
    if is_dir:
        dst_path = dst_path.parent
    if is_wsl:
        dst_wsl = to_wsl_path(dst_path)
        args = ["wsl", "-e"] + to_command_args(
            protocol, src, dst_wsl, is_dir=is_dir, port=port
        )
    else:
        dst = dst_path.as_posix()
        args = to_command_args(protocol, src, dst, is_dir=is_dir, port=port)
    return args


def to_command_args(
    protocol: str,
    src: str,
    dst: str,
    is_dir: bool = False,
    port: int = 22,
) -> list[str]:
    if protocol == "rsync":
        # FIXME: f"--rsh=\"ssh -p {port}\"" should be added here, but it doesn't work
        # because of "No such file or directory (2)"
        if is_dir:
            return ["rsync", "-ar", "--progress", src, dst]
        else:
            return ["rsync", "-a", "--progress", src, dst]
    elif protocol == "scp":
        if is_dir:
            return ["scp", "-P", str(port), "-r", src, dst]
        else:
            return ["scp", "-P", str(port), src, dst]
    raise ValueError(f"Unsupported protocol {protocol!r} (must be 'rsync' or 'scp')")


def to_wsl_path(src: Path) -> str:
    """Convert an absolute Windows path to a WSL path.

    This function must be called in Windows.

    Examples
    --------
    to_wsl_path(Path("C:/Users/me/Documents")) -> "/mnt/c/Users/me/Documents"
    to_wsl_path(Path("D:/path/to/file.txt")) -> "/mnt/d/path/to/file.txt"
    """
    drive = src.drive
    drive_rel = drive + "/"
    wsl_root = Path("mnt") / drive.lower().rstrip(":")
    src_pathobj_wsl = wsl_root / src.relative_to(drive_rel).as_posix()
    return "/" + src_pathobj_wsl.as_posix()


def to_wsl_path_from_wsl(src: str) -> str:
    """Convert a Windows path to a WSL path.

    This function must be called in Windows.

    Examples
    --------
    to_wsl_path_from_wsl("C:/Users/me/Documents") -> "/mnt/c/Users/me/Documents"
    to_wsl_path_from_wsl("D:/path/to/file.txt") -> "/mnt/d/path/to/file.txt"
    """
    src = src.replace("\\", "/")
    if src.startswith("/mnt/"):
        # already in WSL path format. This happens when links are resolved (such as the
        # start menu of Windows).
        return src
    if src[1:3] == ":/":
        drive = src[0].lower()
        return f"/mnt/{drive}/{src[3:]}"
    raise NotImplementedError


def to_windows_path_from_wsl(src: str, distro: str | None = None) -> Path:
    """Convert an absolute WSL path to a Windows UNC path.

    This function must be called in Windows.

    Examples
    --------
    to_windows_path_from_wsl("/home/me/a.txt", "Ubuntu")
    -> Path("//wsl.localhost/Ubuntu/home/me/a.txt")
    """
    if src.startswith("/mnt/") and (len(src) == 6 or src[6] == "/"):
        # path of Windows filesystem
        return Path(f"{src[5].upper()}:/{src[7:]}")
    if src.startswith("~"):
        src = get_wsl_env("HOME") + src[1:]
    if not src.startswith("/"):
        raise ValueError(f"WSL path must be absolute, got {src!r}")
    if distro is None:
        distro = get_wsl_env("WSL_DISTRO_NAME")
    return Path(f"//wsl.localhost/{distro}{src}")


@lru_cache(maxsize=4)
def get_wsl_env(name: str) -> str:
    """Get the environment variable of the default WSL distribution."""
    result = subprocess.run(["wsl", "-e", "printenv", name], capture_output=True)
    if result.returncode != 0:
        raise ValueError(f"Failed to get {name} in WSL: {result.stderr.decode()}")
    return result.stdout.decode().strip()
