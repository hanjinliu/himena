from enum import Enum

BasicTextFileTypes = frozenset(
    [
        ".txt",
        ".md",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".toml",
        ".log",
    ]
)


class StandardTypes(Enum):
    TEXT = "text"
    HTML = "html"
    TABLE = "table"
    IMAGE = "image"

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"
