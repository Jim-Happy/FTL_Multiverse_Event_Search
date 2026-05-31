from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow

from ftl_dao import FTLDAO

from .effects_formatter import EffectsFormatterMixin
from .interaction_handler import InteractionHandlerMixin
from .node_renderer import NodeRendererMixin
from .tree_builder import TreeBuilderMixin
from .tree_navigation import TreeNavigationMixin
from .tree_rendering import TreeRenderingMixin
from .ui_builder import UIBuilderMixin
from .ui_utils import UIUtilsMixin


class FTLSearchMainWindow(
    QMainWindow,
    UIBuilderMixin,
    InteractionHandlerMixin,
    NodeRendererMixin,
    TreeNavigationMixin,
    TreeRenderingMixin,
    TreeBuilderMixin,
    EffectsFormatterMixin,
    UIUtilsMixin,
):
    ROLE_TARGET_ID = int(Qt.ItemDataRole.UserRole)
    ROLE_KIND = ROLE_TARGET_ID + 1
    ROLE_PATH = ROLE_TARGET_ID + 2
    ROLE_LOADED = ROLE_TARGET_ID + 3
    ROLE_RENDER_HTML = ROLE_TARGET_ID + 4

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FTL 事件查询工具")
        self.resize(1280, 800)
        self.dao = FTLDAO()
        self._build_ui()
        self._install_tree_rendering()
        self._load_demo_content()
        self.search_button.clicked.connect(self.on_search)
        self.search_input.returnPressed.connect(self.on_search)
        self.event_list.currentItemChanged.connect(self.on_event_list_current_item_changed)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self.dao.close()
        finally:
            super().closeEvent(event)


def run_app() -> int:
    app = QApplication(sys.argv)
    window = FTLSearchMainWindow()
    window.show()
    return app.exec()
