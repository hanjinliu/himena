import sys
from enum import Enum
from types import SimpleNamespace

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        pass


BasicTextFileTypes = frozenset(
    [".txt", ".md", ".json", ".xml", ".yaml", ".yml", ".toml", ".log", ".py", ".pyi",
     ".pyx", ".c", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".html", ".css",
     ".scss", ".sass", ".php", ".rb", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".bat",
     ".cmd", ".m", ".vbs", ".vba", ".r", ".rs", ".go"]
)  # fmt: skip

ConventionalTextFileNames = frozenset(
    ["LICENSE", "Makefile", "dockerfile", ".gitignore", ".gitattributes", ".vimrc",
     ".viminfo", ".pypirc"]
)  # fmt: skip


class StandardTypes(SimpleNamespace):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


class StandardSubtypes(SimpleNamespace):
    HTML = "text.html"


class MenuId(StrEnum):
    FILE = "file"
    FILE_RECENT = "file/recent"
    FILE_NEW = "file/new"
    FILE_SCREENSHOT = "file/screenshot"
    WINDOW = "window"
    WINDOW_RESIZE = "window/resize"
    WINDOW_ALIGN = "window/align"
    WINDOW_ANCHOR = "window/anchor"
    WINDOW_NTH = "window/nth"
    VIEW = "view"
    TOOLS = "tools"
    TOOLS_TEXT = "tools/text"
    TOOLBAR = "toolbar"

    def __str__(self) -> str:
        return self.value


class ActionCategory(StrEnum):
    OPEN_RECENT = "open-recent"
    GOTO_WINDOW = "go-to-window"
