from __future__ import annotations

from pathlib import Path, PurePosixPath


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


def wsl_to_local(src: str, dst: Path, is_dir: bool = False) -> list[str]:
    """Copy a file from WSL to local Windows filesystem."""
    if is_dir:
        dst = dst.parent
    wsl_dst = to_wsl_path(dst)
    if is_dir:
        args = ["wsl", "-e", "cp", "-r", src, wsl_dst]
    else:
        args = ["wsl", "-e", "cp", src, wsl_dst]
    return args


def local_to_wsl(src: Path, dst: str, is_dir: bool = False) -> list[str]:
    """Copy a file from local Windows filesystem to WSL."""
    if is_dir:
        dst = PurePosixPath(dst).parent.as_posix()
    wsl_src = to_wsl_path(src)
    if is_dir:
        args = ["wsl", "-e", "cp", "-r", wsl_src, dst]
    else:
        args = ["wsl", "-e", "cp", wsl_src, dst]
    return args
