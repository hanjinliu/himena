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
