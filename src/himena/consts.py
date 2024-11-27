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

# Allowed for profile names
ALLOWED_LETTERS = string.ascii_letters + string.digits + "_- "


class StandardType(SimpleNamespace):
    """Conventions for standard model types."""

    ### Basic types ###
    TEXT = "text"  # any text
    TABLE = "table"  # 2D data without any special structure
    ARRAY = "array"  # nD grid data such as numpy array
    PARAMETERS = "parameters"  # dictionary of parameters
    DATAFRAME = "dataframe"  # DataFrame object
    EXCEL = "excel"  # Excel file (~= tabbed tables)

    ### Subtypes ###
    # HTML text
    HTML = "text.html"

    # SVG text
    SVG = "text.svg"

    # image data
    IMAGE = "array.image"
    # binary image data that will be used as a mask
    IMAGE_BINARY = "array.image.binary"
    # image label data (e.g., segmentation)
    IMAGE_LABELS = "array.image.labels"

    # 1D numerical array
    ARRAY_1D = "array.1d"

    # (N, D) numerical array, such as D-dimensional point cloud
    COORDINATES = "array.coordinates"

    ### plotting ###
    PLOT = "plot"  # objects that plot standard
    MPL_FIGURE = "matplotlib-figure"  # matplotlib figure object

    ### 3D ###
    SURFACE = "surface"  # vertices, faces and values for 3D surface plot

    IPYNB = "ipynb"  # Jupyter notebook file

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


class ParametricWidgetProtocolNames:
    GET_PARAMS = "get_params"
    GET_OUTPUT = "get_output"
    IS_PREVIEW_ENABLED = "is_preview_enabled"
    CONNECT_CHANGED_SIGNAL = "connect_changed_signal"


NO_RECORDING_FIELD = "__himena_no_recording__"
