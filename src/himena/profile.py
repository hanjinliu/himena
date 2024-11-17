from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterable
import warnings
from platformdirs import user_data_dir
from pydantic import field_validator
from pydantic_compat import BaseModel, Field
from himena.consts import ALLOWED_LETTERS

USER_DATA_DIR = Path(user_data_dir("himena"))


@contextmanager
def patch_user_data_dir(path: str | Path):
    """Change the user data directory to avoid pytest updates the local state."""
    global USER_DATA_DIR
    old = USER_DATA_DIR
    USER_DATA_DIR = Path(path)
    try:
        yield
    finally:
        USER_DATA_DIR = old


def data_dir() -> Path:
    """Get the user data directory."""
    if not USER_DATA_DIR.exists():
        USER_DATA_DIR.mkdir(parents=True)
    return USER_DATA_DIR


def profile_dir() -> Path:
    _dir = data_dir() / "profiles"
    if not _dir.exists():
        _dir.mkdir(parents=True)
    return _dir


def _default_plugins() -> list[str]:
    """Factory function for the default plugin list."""
    out = []
    _builtins_dir = Path(__file__).parent.joinpath("builtins")
    for path in _builtins_dir.joinpath("qt").glob("*"):
        if path.name == "__pycache__":
            continue
        out.append(f"himena.builtins.qt.{path.name}")
    out.append("himena.builtins.tools")
    for path in _builtins_dir.glob("*.py"):
        out.append(f"himena.builtins.{path.stem}")
    return out


class AppProfile(BaseModel):
    """Model of a profile."""

    name: str = Field(default="default", description="Name of the profile.")
    plugins: list[str] = Field(
        default_factory=_default_plugins, description="List of plugins to load."
    )
    theme: str = Field(default="light-purple", description="Theme to use.")

    @classmethod
    def from_json(cls, path) -> "AppProfile":
        """Construct an AppProfile from a json file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def default(self) -> "AppProfile":
        """Return the default profile."""
        return AppProfile()

    def save(self, path):
        """Save profile as a json file."""
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=4)
        return None

    @field_validator("name")
    def _validate_name(cls, value):
        # check if value is a valid file name
        if not all(c in ALLOWED_LETTERS for c in value):
            raise ValueError(f"Invalid profile name: {value}")
        return value


def load_app_profile(name: str) -> AppProfile:
    path = profile_dir() / f"{name}.json"
    if path.exists():
        return AppProfile.from_json(path)
    return AppProfile.default()


def iter_app_profiles() -> Iterable[AppProfile]:
    for path in profile_dir().glob("*.json"):
        try:
            yield AppProfile.from_json(path)
        except Exception:
            warnings.warn(f"Could not load profile {path}.")


def define_app_profile(name: str, plugins: list[str]):
    path = profile_dir() / f"{name}.json"
    profile = AppProfile(name=name, plugins=plugins)
    profile.save(path)
    return None
