import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        pass


BasicTextFileTypes = frozenset(
    [".txt", ".md", ".json", ".xml", ".yaml", ".yml", ".toml", ".log", ".py", ".pyi",
     ".pyx", ".c", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".html", ".css",
     ".scss", ".sass", ".php", ".rb", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".bat",
     ".cmd", ".m", ".vbs", ".vba", ".r", ".rs",
    ]
)  # fmt: skip

ConventionalTextFileNames = frozenset(
    ["LICENSE", "Makefile", "dockerfile", ".gitignore", ".gitattributes", ".vimrc",
     ".viminfo", ".pypirc",
    ]
)  # fmt: skip


class StandardTypes(StrEnum):
    TEXT = "text"
    HTML = "html"
    TABLE = "table"
    IMAGE = "image"

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class MenuId(StrEnum):
    FILE = "file"
    FILE_RECENT = "file/recent"
    FILE_NEW = "file/new"
    FILE_SCREENSHOT = "file/screenshot"
    WINDOW = "window"
    WINDOW_ALIGN = "window/align"
    WINDOW_ANCHOR = "window/anchor"
    WINDOW_EXIT = "window/exit"
    TAB = "tab"
    VIEW = "view"
    TOOLBAR = "toolbar"
    WINDOW_TITLE_BAR = "window_title_bar"
    WINDOW_TITLE_BAR_ALIGN = "window_title_bar/align"
    WINDOW_TITLE_BAR_ANCHOR = "window_title_bar/anchor"

    def __str__(self) -> str:
        return self.value


class ActionCategory(StrEnum):
    OPEN_RECENT = "open-recent"
