from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Iterable
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

    name: str = Field(
        default="default", description="Name of the profile.", frozen=True
    )
    plugins: list[str] = Field(
        default_factory=_default_plugins, description="List of plugins to load."
    )
    theme: str = Field(default="light-green", description="Theme to use.")
    startup_commands: list[tuple[str, dict[str, Any] | None]] = Field(
        default_factory=list,
        description="Startup commands that will be executed when the app starts.",
    )

    @classmethod
    def from_json(cls, path) -> "AppProfile":
        """Construct an AppProfile from a json file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def default(cls, save: bool = False) -> "AppProfile":
        """Return the default profile."""
        prof = AppProfile()
        if save and not (profile_dir() / f"{prof.name}.json").exists():
            prof.save()
        return prof

    def save(self, path: str | Path | None = None) -> None:
        """Save profile as a json file."""
        if path is None:
            path = profile_dir() / f"{self.name}.json"
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=4)
        return None

    def with_name(self, name: str) -> "AppProfile":
        """Return a new profile with a new name."""
        return self.model_copy(update={"name": name})

    def with_plugins(self, plugins: list[str]) -> "AppProfile":
        """Return a new profile with new plugins."""
        return self.model_copy(update={"plugins": plugins})

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
    raise ValueError(
        f"Profile {name!r} does not exist. Please create a new profile with:\n"
        f"$ himena {name} --new"
    )


def iter_app_profiles() -> Iterable[AppProfile]:
    for path in profile_dir().glob("*.json"):
        try:
            yield AppProfile.from_json(path)
        except Exception:
            warnings.warn(f"Could not load profile {path}.")


def define_app_profile(name: str, plugins: list[str]):
    """Define (probably upadte) a profile."""
    path = profile_dir() / f"{name}.json"
    profile = AppProfile(name=name, plugins=plugins)
    profile.save(path)
    return None


def new_app_profile(name: str) -> None:
    """Create a new profile."""
    path = profile_dir() / f"{name}.json"
    if path.exists():
        raise ValueError(f"Profile {name!r} already exists.")
    profile = AppProfile.default().with_name(name)
    return profile.save(path)


def remove_app_profile(name: str) -> None:
    """Remove an existing profile."""
    path = profile_dir() / f"{name}.json"
    return path.unlink()
