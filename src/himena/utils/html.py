import re
import html

HTML_PATTERN = re.compile(r"<.*?>")
HTML_BLOCK_PATTERN = re.compile(r"<html>.*?</html>", re.DOTALL)
HEADER_PATTERN = re.compile(r"<head>.*?</head>", re.DOTALL)
NEWLINE_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)
P_PATTERN = re.compile(r"<p.*?>(.*?)</p>", re.DOTALL)


def html_to_plain_text(html_text: str) -> str:
    """Convert HTML text to plain text."""
    html_text = html_text.replace("\n", "")
    if html_block_match := HTML_BLOCK_PATTERN.search(html_text):
        html_text = html_block_match.group(0)
    html_text = NEWLINE_PATTERN.sub("\n", html_text)
    html_text = "\n".join(m.group(1) for m in P_PATTERN.finditer(html_text))
    return html.unescape(HTML_PATTERN.sub("", HEADER_PATTERN.sub("", html_text)))
