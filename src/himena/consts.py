import sys
from enum import Enum
import string
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
     ".viminfo", ".pypirc", "MANIFEST.in",]
)  # fmt: skip

ExcelFileTypes = frozenset(
    [".xls", ".xlsx", ".xlsm", ".xlsb", ".xltx", ".xltm", ".xlam"]
)  # fmt: skip

# Monospace font
if sys.platform == "win32":
    MonospaceFontFamily = "Consolas"
elif sys.platform == "darwin":
    MonospaceFontFamily = "Menlo"
else:
    MonospaceFontFamily = "Monospace"

ALLOWED_LETTERS = string.ascii_letters + string.digits + "_- "


class StandardType(SimpleNamespace):
    TEXT = "text"
    TABLE = "table"
    ARRAY = "array"
    PARAMETERS = "parameters"
    DATAFRAME = "dataframe"
    EXCEL = "excel"


class StandardSubtype(SimpleNamespace):
    HTML = "text.html"
    IMAGE = "array.image"
    ARRAY_1D = "array.1d"
    ARRAY_2D = "array.2d"
    ARRAY_3D = "array.3d"
    ARRAY_4D = "array.4d"
    ARRAY_5D = "array.5d"


class MenuId(StrEnum):
    FILE = "file"
    FILE_RECENT = "file/recent"
    FILE_NEW = "file/new"
    FILE_SAMPLES = "file/samples"
    FILE_SCREENSHOT = "file/screenshot"
    WINDOW = "window"
    WINDOW_RESIZE = "window/resize"
    WINDOW_ALIGN = "window/align"
    WINDOW_ANCHOR = "window/anchor"
    WINDOW_NTH = "window/nth"
    VIEW = "view"
    TOOLS = "tools"
    TOOLBAR = "toolbar"
    RECENT_ALL = ".recent-all"

    def __str__(self) -> str:
        return self.value


class ActionCategory(StrEnum):
    OPEN_RECENT = "open-recent"
    GOTO_WINDOW = "go-to-window"
