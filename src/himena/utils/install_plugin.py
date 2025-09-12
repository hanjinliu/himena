from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
import subprocess
from abc import ABC, abstractmethod


class BaseInstallTool(ABC):
    """Abstract base class for installation tools like pip and uv."""

    @abstractmethod
    def args_install(self, packages: list[str]) -> list[str]:
        raise NotImplementedError

    def install(self, packages: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(self.args_install(packages), check=True)


class PipInstallTool(BaseInstallTool):
    def args_install(self, packages: list[str]) -> list[str]:
        return [sys.executable, "-m", "pip", "install", "-U", *packages]


class UvInstallTool(BaseInstallTool):
    def args_install(self, packages: list[str]) -> list[str]:
        return ["uv", "pip", "install", "-U", *packages]


@lru_cache(maxsize=1)
def get_install_tool() -> BaseInstallTool:
    """Get the appropriate installation tool based on the environment."""
    env_dir = Path(sys.executable).parent.parent
    if (venv_cfg_path := env_dir.joinpath("pyvenv.cfg")).exists():
        venv_cfg_dict = _parse_venv_cfg(venv_cfg_path)
        if "uv" in venv_cfg_dict:
            return UvInstallTool()
    return PipInstallTool()


def _parse_venv_cfg(path: Path) -> dict[str, str]:
    cfg = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            cfg[key.strip()] = value.strip()
    return cfg
