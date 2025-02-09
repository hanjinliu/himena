import re
from pathlib import Path
from textwrap import dedent
from imageio import imwrite
import mkdocs_gen_files

from himena import new_window
from himena.qt._qsub_window import get_subwindow
from himena.qt._utils import ArrayQImage

DOCS: Path = Path(__file__).parent.parent
CODE_BLOCK = re.compile("``` ?python image=.*?\n([^`]*)```")


def main() -> None:
    ui = new_window()
    for mdfile in sorted(DOCS.rglob("*.md"), reverse=True):
        md = mdfile.read_text()
        code_blocks = list(CODE_BLOCK.finditer(md))
        namespace = {"ui": ui}
        for match in code_blocks:
            file_name = match.group(0).split("python image=")[1].splitlines()[0]
            if file_name[0] == file_name[-1] == '"':
                file_name = file_name[1:-1]
            code = dedent(match.group(1)).strip()
            try:
                exec(code, namespace, {})
            except Exception as e:
                print(f"Error in\n\n{code}\n\n")
                raise e
            subwin = get_subwindow(ui.current_window.widget)
            arr = ArrayQImage.from_qwidget(subwin).to_numpy()
            dest = f"_images/screenshot-{file_name}.png"
            with mkdocs_gen_files.open(dest, "wb") as f:
                imwrite(f.name, arr, format="png")

main()
