import json
from pathlib import Path
from typing import TYPE_CHECKING
from pydantic_compat import BaseModel
from himena.utils.misc import iter_subclasses

if TYPE_CHECKING:
    from typing import Self

_META_NAME = "meta.json"
_CLASS_JSON = ".class.json"


class BaseMetadata(BaseModel):
    """The base class for a model metadata."""

    @classmethod
    def from_metadata(cls, dir_path: Path) -> "Self":
        """Construct the metadata from a directory."""
        return cls.model_validate_json(dir_path.joinpath(_META_NAME).read_text())

    def write_metadata(self, dir_path: Path) -> None:
        """Write the metadata to a directory."""
        dir_path.joinpath(_META_NAME).write_text(self.model_dump_json())

    def expected_type(self) -> str | None:
        """Return the expected type of the metadata. None if not applicable."""
        return None

    def _class_info(self) -> dict:
        return {"name": self.__class__.__name__, "module": self.__class__.__module__}

    def _repr_pretty_(self, p, cycle):
        """Pretty print the metadata."""
        lines = [f"{self.__class__.__name__}("]
        for key, value in self.__repr_args__():
            lines.append(f"  {key}={value!r},")
        lines.append(")")
        p.text("\n".join(lines))


def read_metadata(dir_path: Path) -> BaseMetadata:
    """Read the metadata from a directory."""
    with dir_path.joinpath(_CLASS_JSON).open("r") as f:
        class_js = json.load(f)
    module = class_js["module"]
    name = class_js["name"]
    for sub in iter_subclasses(BaseMetadata):
        if sub.__name__ == name and sub.__module__ == module:
            metadata_class = sub
            break
    else:
        raise ValueError(f"Metadata class {name=}n {module=} not found.")

    return metadata_class.from_metadata(dir_path)


def write_metadata(meta: BaseMetadata, dir_path: Path) -> None:
    """Write the metadata to a directory."""
    meta.write_metadata(dir_path)
    with dir_path.joinpath(_CLASS_JSON).open("w") as f:
        json.dump(meta._class_info(), f)
    return None
