from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.plugins import validate_protocol

if TYPE_CHECKING:
    from email.message import Message


class QEmailView(QtW.QWidget):
    """A widget for displaying email content."""

    __himena_widget_id__ = "builtins:QEmailView"
    __himena_display_name__ = "Built-in E-mail Viewer"

    def __init__(self):
        super().__init__()
        self._line_from = QLabeledLineEdit("From")
        self._line_to = QLabeledLineEdit("To")
        self._time_sent = QLabeledLineEdit("Sent")
        self._subject = QLabeledLineEdit("Subject")
        self._content_view = QtW.QTextEdit()
        self._content_view.setReadOnly(True)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._line_from)
        layout.addWidget(self._line_to)
        layout.addWidget(self._subject)
        layout.addWidget(self._time_sent)
        layout.addWidget(self._content_view)
        self._email_msg_object: Message | None = None

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        """Update the widget to display the email content from the data model."""
        from email.message import Message

        if not isinstance(content := model.value, Message):
            raise ValueError(f"Expected an EmailMessage object, got {type(content)}")
        email_content = EMailContent.from_msg(content)
        self._set_email_content(email_content)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        """Convert the current state of the widget back to a data model."""
        if self._email_msg_object is None:
            raise ValueError("No email message is currently loaded in the widget.")
        return WidgetDataModel(
            type=StandardType.EMAIL,
            value=self._email_msg_object,
        )

    @validate_protocol
    def size_hint(self):
        return 480, 520

    def _set_email_content(self, content: EMailContent):
        self._line_from.setText(content.email_from)
        self._line_to.setText(content.email_to)
        self._subject.setText(content.subject)
        self._time_sent.setText(content.date)
        if content.html:
            self._content_view.setHtml(content.html)
        else:
            self._content_view.setPlainText(content.text)


class QLabeledLineEdit(QtW.QWidget):
    """A simple widget that combines a QLabel and a QLineEdit for labeled input."""

    def __init__(self, label: str):
        super().__init__()
        self._label = QtW.QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._line_edit = QtW.QLineEdit()
        self._line_edit.setReadOnly(True)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        layout.addWidget(self._line_edit)
        self.setLabelWidth(60)
        self.setLabel(label)

    def setLabel(self, text: str):
        self._label.setText(f"<font color='gray'>{text}:</font>")

    def setLabelWidth(self, width: int):
        self._label.setFixedWidth(width)

    def setText(self, text: str):
        self._line_edit.setText(text)


@dataclass
class EMailContent:
    email_from: str
    email_to: str
    subject: str
    date: str
    text: str
    html: str
    # TODO: attatchment

    @classmethod
    def from_msg(cls, msg: Message) -> EMailContent:
        text = ""
        html = ""
        subject = msg.get("Subject", "")
        email_from = msg.get("From", "")
        email_to = msg.get("To", "")
        date = msg.get("Date", "")

        for part in msg.walk():
            content_type = part.get_content_type()

            if content_type == "text/plain":
                text += part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8"
                )
            elif content_type == "text/html":
                html += part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8"
                )

        return EMailContent(
            email_from=email_from,
            email_to=email_to,
            subject=subject,
            date=date,
            text=text,
            html=html,
        )
