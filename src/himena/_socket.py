from __future__ import annotations

from pathlib import Path
from io import TextIOWrapper
import socket
from dataclasses import dataclass, asdict
import yaml
from pydantic import BaseModel, Field


def lock_file_path(name: str, port: int) -> Path:
    """Get the lock file path."""
    from himena.profile import data_dir

    dir_path = data_dir() / "lock"
    if not dir_path.exists():
        dir_path.mkdir(parents=True)
    return dir_path / f"{name}+{port}.lock"


def get_unique_lock_file(name: str, port: int) -> TextIOWrapper | None:
    """Create a lock file, return None if it already exists."""
    lock_file = lock_file_path(name, port)
    if lock_file.exists():
        return None
    return lock_file.open("w")


@dataclass
class SocketInfo:
    host: str = "localhost"
    port: int = 49200

    def asdict(self) -> dict[str, int | str]:
        """Convert to a dictionary."""
        return asdict(self)

    @classmethod
    def from_lock(cls, name: str, port: int) -> SocketInfo:
        """Get the socket info from the lock file."""
        with lock_file_path(name, port).open("r") as f:
            yml = yaml.load(f, Loader=yaml.Loader)
        if yml is None:
            yml = {}
        return SocketInfo(
            host=yml.get("host", "localhost"), port=yml.get("port", 49200)
        )

    def dump(self, path):
        yaml.dump(self.asdict(), path)

    def send_to_window(self, profile: str, files: list[str] | None = None) -> bool:
        """Send data to the window."""
        data = InterProcessData(
            profile_name=profile,
            files=files or [],
        )
        try:
            data.send(self.host, self.port)
        except Exception as e:
            print(f"Socket is not available: {e}")
            return False
        else:
            print(f"Sent data to {profile!r} window at {self.host}:{self.port}.")
            return True


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
