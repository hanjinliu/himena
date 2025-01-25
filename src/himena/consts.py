import sys
import string
from types import SimpleNamespace, MappingProxyType
from himena.utils.enum import StrEnum


BasicTextFileTypes = frozenset(
    [".txt", ".md", ".json", ".xml", ".yaml", ".yml", ".toml", ".log", ".py", ".pyi",
     ".pyx", ".c", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".html", ".htm", ".css",
     ".scss", ".sass", ".php", ".rb", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".bat",
     ".cmd", ".m", ".vbs", ".vba", ".r", ".rs", ".go", ".svg", ".tex", ".rst", ".ipynb",
     ".lock", ".cs"]
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
    """Conventions for standard model types.

    Developers should use these types as much as possible to ensure compatibility with
    other plugins.
    """

    ### Basic types ###
    TEXT = "text"  # any text
    TABLE = "table"  # 2D data without any special structure
    ARRAY = "array"  # nD grid data such as numpy array
    DICT = "dict"  # dictionary
    DATAFRAME = "dataframe"  # DataFrame object
    EXCEL = "excel"  # Excel file (~= tabbed tables)

    ### Subtypes ###
    # text subtypes
    HTML = "text.html"  # HTML text
    SVG = "text.svg"  # SVG text
    MARKDOWN = "text.markdown"  # markdown text
    JSON = "text.json"  # JSON text
    IPYNB = "text.json.ipynb"  # Jupyter notebook

    # image data
    IMAGE = "array.image"
    # uint image data that will be interpreted as labels
    IMAGE_LABELS = "array.image.labels"

    # (N, D) numerical array, such as D-dimensional point cloud
    COORDINATES = "array.coordinates"

    # DataFrame that is supposed to be plotted immediately (such as image line scan)
    DATAFRAME_PLOT = "dataframe.plot"

    ### plotting ###
    PLOT = "plot"  # objects that satisfy the plotting standard
    MPL_FIGURE = "matplotlib-figure"  # matplotlib figure object

    ### 3D ###
    MESH = "mesh"  # vertices, faces and values for 3D mesh

    ### Nested models ###
    MODELS = "models"  # list or dict of models
    LAZY = "lazy"  # lazy loading of models

    ### Other types ###
    WORKFLOW = "workflow"  # himena workflow object
    GROUPBY = "groupby"  # DataFrame GroupBy object
    ROIS = "rois"  # regions of interest
    FUNCTION = "function"  # callable object
    FUNCTION_PARTIAL = "function.partial"  # callable object
    DISTRIBUTION = "distribution"  # probablistic distribution object

    # fallback when no reader is found for the file (which means that the file could be
    # opened as a text file)
    READER_NOT_FOUND = "reader_not_found"

    # fallback when no specific widget can be used for the data
    ANY = "any"


class MenuId(StrEnum):
    FILE = "file"
    FILE_RECENT = "file/recent"
    FILE_NEW = "file/new"
    FILE_SCREENSHOT = "file/screenshot"
    FILE_SESSION = "file/session"
    WINDOW = "window"
    WINDOW_RESIZE = "window/resize"
    WINDOW_ALIGN = "window/align"
    WINDOW_ANCHOR = "window/anchor"
    WINDOW_NTH = "window/nth"
    WINDOW_LAYOUT = "window/layout"
    VIEW = "view"
    TOOLS = "tools"
    TOOLS_DOCK = "tools/dock"
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
    GET_TITLE = "get_title"
    GET_AUTO_CLOSE = "auto_close"
    GET_AUTO_SIZE = "auto_size"


NO_RECORDING_FIELD = "__himena_no_recording__"

PYDANTIC_CONFIG_STRICT = MappingProxyType(
    {
        "revalidate_instances": "always",
        "strict": True,
        "validate_assignment": True,
    }
)
