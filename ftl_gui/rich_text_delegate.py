from __future__ import annotations

from PyQt6.QtCore import QSize, QRectF, Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import QApplication, QStyledItemDelegate, QStyle, QStyleOptionViewItem


class RichTextItemDelegate(QStyledItemDelegate):
    def __init__(self, html_role: int, parent=None) -> None:
        super().__init__(parent)
        self._html_role = html_role

    def _build_document(self, option: QStyleOptionViewItem, index) -> QTextDocument:
        html_text = index.data(self._html_role)
        if not html_text:
            html_text = index.data(Qt.ItemDataRole.DisplayRole)

        document = QTextDocument()
        document.setDefaultFont(option.font)
        document.setDocumentMargin(0)
        document.setHtml(str(html_text or ""))
        return document

    def paint(self, painter, option, index) -> None:  # type: ignore[override]
        html_text = index.data(self._html_role)
        if not html_text:
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""

        style = opt.widget.style() if opt.widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        text_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget)
        if text_rect.width() <= 0 or text_rect.height() <= 0:
            text_rect = opt.rect.adjusted(8, 4, -8, -4)

        document = self._build_document(opt, index)
        document.setTextWidth(max(1, text_rect.width()))

        painter.save()
        painter.translate(text_rect.topLeft())
        document.drawContents(painter, QRectF(0, 0, text_rect.width(), text_rect.height()))
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # type: ignore[override]
        html_text = index.data(self._html_role)
        if not html_text:
            return super().sizeHint(option, index)

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        document = self._build_document(opt, index)

        width = opt.rect.width()
        widget = opt.widget
        if width <= 0 and widget is not None and hasattr(widget, "viewport"):
            width = widget.viewport().width()
        if width <= 0:
            width = 420

        document.setTextWidth(max(160, width - 24))
        size = document.size().toSize()
        return QSize(width, size.height() + 8)
