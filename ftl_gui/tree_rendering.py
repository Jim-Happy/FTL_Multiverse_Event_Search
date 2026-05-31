from __future__ import annotations

from PyQt6.QtCore import Qt

from .rich_text_delegate import RichTextItemDelegate


class TreeRenderingMixin:
    def _install_tree_rendering(self) -> None:
        self.tree_widget.setUniformRowHeights(False)
        self.tree_widget.setWordWrap(True)
        self.tree_widget.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tree_widget.setItemDelegate(RichTextItemDelegate(self.ROLE_RENDER_HTML, self.tree_widget))
