from __future__ import annotations

from pathlib import Path


def local_to_remote(
    protocol: str,
    src: Path,
    dst: str,
    is_wsl: bool = False,
    is_dir: bool = False,
) -> list[str]:
    """Send local file to the remote host."""
    if is_wsl:
        src_wsl = to_wsl_path(src)
        args = ["wsl", "-e"] + to_command_args(protocol, src_wsl, dst, is_dir)
    else:
        args = to_command_args(protocol, src.as_posix(), dst, is_dir)
    return args


def remote_to_local(
    protocol: str,
    src: str,
    dst_path: Path,
    is_wsl: bool = False,
    is_dir: bool = False,
) -> list[str]:
    """Run scp/rsync command to move the file from remote to local `dst_path`."""
    if is_wsl:
        dst_wsl = to_wsl_path(dst_path)
        args = ["wsl", "-e"] + to_command_args(protocol, src, dst_wsl, is_dir=is_dir)
    else:
        dst = dst_path.as_posix()
        args = to_command_args(protocol, src, dst, is_dir=is_dir)
    return args


def to_command_args(
    protocol: str,
    src: str,
    dst: str,
    is_dir: bool = False,
) -> list[str]:
    if protocol == "rsync":
        if is_dir:
            return ["rsync", "-ar", "--progress", src, dst]
        else:
            return ["rsync", "-a", "--progress", src, dst]
    elif protocol == "scp":
        if is_dir:
            return ["scp", "-r", src, dst]
        else:
            return ["scp", src, dst]
    raise ValueError(f"Unsupported protocol {protocol!r} (must be 'rsync' or 'scp')")


def to_wsl_path(src: Path) -> str:
    """Convert an absolute Windows path to a WSL path.

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
