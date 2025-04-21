from __future__ import annotations

from platformdirs import user_data_dir
from pathlib import Path
from io import TextIOWrapper
import socket
from dataclasses import dataclass, asdict
import yaml
from pydantic import BaseModel, Field

USER_DATA_DIR = Path(user_data_dir("himena"))


def lock_file_path(name: str) -> Path:
    """Get the lock file path."""
    return USER_DATA_DIR / "lock" / f"{name}.lock"


def get_unique_lock_file(name: str) -> TextIOWrapper | None:
    """Create a lock file, return None if it already exists."""
    lock_file = lock_file_path(name)
    if lock_file.exists():
        return None
    if not lock_file.parent.exists():
        lock_file.parent.mkdir(parents=True)
    return lock_file_path(name).open("w")


def get_socket_info_from_lock_file(name: str) -> SocketInfo:
    """Get the socket info from the lock file."""
    with lock_file_path(name).open("r") as f:
        yml = yaml.load(f, Loader=yaml.Loader)
    return SocketInfo(host=yml["host"], port=yml["port"])


@dataclass
class SocketInfo:
    host: str = "localhost"
    port: int = 49200

    def asdict(self) -> dict[str, int | str]:
        """Convert to a dictionary."""
        return asdict(self)


class InterProcessData(BaseModel):
    """Data to be sent over the socket."""

    profile_name: str = Field(..., description="Name of the profile")
    files: list[str] = Field(default_factory=list, description="List of files to send")

    def to_bytes(self) -> bytes:
        """Convert the data to bytes."""
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> InterProcessData:
        """Convert bytes back to the data model."""
        return cls.model_validate_json(data.decode("utf-8"))

    def send(self, host: str = "localhost", port: int = 49200) -> None:
        """Send the data to the specified host and port using a socket."""
        with socket.create_connection((host, port)) as sock:
            sock.sendall(self.to_bytes())


def send_to_window(
    profile: str = "default",
    files: list[str] | None = None,
    host: str = "localhost",
    port: int = 49200,
):
    data = InterProcessData(
        profile_name=profile,
        files=files or [],
    )
    try:
        data.send(host, port)
    except Exception as e:
        raise RuntimeError(
            "Socket is not available. Make sure the application is running."
        ) from e
    else:
        print(f"Sent data to {profile} window at {host}:{port}.")
