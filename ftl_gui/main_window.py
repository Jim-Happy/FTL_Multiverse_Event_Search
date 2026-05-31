from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

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
        self._set_app_icon()
        self.dao = FTLDAO()
        self._build_menu_bar()
        self._build_ui()
        self._install_tree_rendering()
        self._load_demo_content()
        self.search_button.clicked.connect(self.on_search)
        self.search_input.returnPressed.connect(self.on_search)
        self.event_list.currentItemChanged.connect(self.on_event_list_current_item_changed)

    def _icon_path(self) -> Path:
        frozen_root = getattr(sys, "_MEIPASS", None)
        if frozen_root is not None:
            return Path(frozen_root) / "icon" / "icon.ico"
        return Path(__file__).resolve().parents[1] / "icon" / "icon.ico"

    def _set_app_icon(self) -> None:
        icon = QIcon(str(self._icon_path()))
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)

    def _build_menu_bar(self) -> None:
        help_menu = self.menuBar().addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _show_about_dialog(self) -> None:
        html = (
            '<h2>FTL 事件查询器 (Multiverse)</h2>'
            '<p><b>版本：</b> v1.0.0</p>'
            '<p><b>作者：</b> 皓月如心</p>'
            '<p><b>github：</b> <a href="https://github.com/Jim-Happy/FTL_Multiverse_Event_Search">'
            'https://github.com/Jim-Happy/FTL_Multiverse_Event_Search</a></p>'
            '<hr>'
            '<p><b>说明：</b></p>'
            '<p>本工具专为 FTL Multiverse 模组开发。<br>'
            '支持本地化数据解析、事件树追踪及底层奖励透视。</p>'
            '<p><b>特别鸣谢：</b> FTL 汉化组，SlipstreamModManager开发者及 Mod 开发者们</p>'
        )
        QMessageBox.about(self, "关于", html)

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
