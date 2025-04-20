from __future__ import annotations

import socket
from pydantic import BaseModel, Field


def is_socket_used(host: str = "localhost", port: int = 49200) -> bool:
    """Check if the socket is active."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.bind((host, port))
    except OSError:
        return True  # Socket is already in use
    else:
        client.close()
        return False


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
):
    data = InterProcessData(profile_name=profile, files=files or [])
    try:
        data.send()
    except Exception as e:
        raise RuntimeError(
            "Socket is not available. Make sure the application is running."
        ) from e
