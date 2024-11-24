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
    """Conventions for standard model types."""

    TEXT = "text"  # any text
    TABLE = "table"  # 2D data without any special structure
    ARRAY = "array"  # nD grid data such as numpy array
    PARAMETERS = "parameters"  # dictionary of parameters
    DATAFRAME = "dataframe"  # DataFrame object
    EXCEL = "excel"  # Excel file (~= tabbed tables)

    # subtypes
    HTML = "text.html"  # HTML text
    IMAGE = "array.image"  # image data
    ARRAY_1D = "array.1d"  # 1D array, a special case of "array"
    COORDINATES = "array.coordinates"  # (N, D) array, such as D-dimensional point cloud

    # plotting
    PLOT = "plot"  # objects that plot standard

    # fallback when no reader is found for the file (which means that the file could be
    # opened as a text file)
    READER_NOT_FOUND = "reader_not_found"


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
    HELP = "help"

    RECENT_ALL = "file/.recent-all"
    STARTUP = "file/.startup"
    MODEL_MENU = "/model_menu"

    def __str__(self) -> str:
        return self.value


class ActionCategory(StrEnum):
    OPEN_RECENT = "open-recent"
    GOTO_WINDOW = "go-to-window"


class ActionGroup(StrEnum):
    RECENT_FILE = "00_recent_files"
    RECENT_SESSION = "21_recent_sessions"


NO_RECORDING_FIELD = "__himena_no_recording__"
