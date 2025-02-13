from __future__ import annotations

import os
from pathlib import Path
import re
import warnings
from typing import TYPE_CHECKING, Any


warnings.simplefilter("ignore", DeprecationWarning)

if TYPE_CHECKING:
    from mkdocs.structure.pages import Page


def on_page_markdown(md: str, page: Page, **kwargs: Any) -> str:
    """Called when mkdocs is building the markdown for a page."""
    if Path(page.file.src_path).name != "builtin_widgets.md":
        return md

    def _add_images(matchobj: re.Match[str]) -> str:
        file_name = matchobj.group(0).split("python image=")[1].splitlines()[0]
        code = matchobj.group(1)
        if file_name[0] == file_name[-1] == '"':
            file_name = file_name[1:-1]
        reldepth = "../" * page.file.src_path.count(os.sep)
        dest = f"{reldepth}_images/screenshot-{file_name}.png"
        link = f"\n![{file_name}]({dest}){{ loading=lazy, width=360px }}\n\n"

        return f"<div class=\"grid\" markdown>\n{link}\n\n``` python\n{code}```\n</div>"

    md = re.sub("``` ?python image=.*?\n([^`]*)```", _add_images, md)

    return md
