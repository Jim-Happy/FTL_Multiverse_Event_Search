from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)


class UIBuilderMixin:
    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入事件名称、关键字或 ID")
        self.search_button = QPushButton("搜索")
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_button)

        self.event_list = QListWidget()
        self.event_list.setAlternatingRowColors(True)

        left_layout.addLayout(search_row)
        left_layout.addWidget(self.event_list, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.interactive_tab = self._build_interactive_tab()
        self.tree_tab = self._build_tree_tab()
        self.tabs.addTab(self.interactive_tab, "交互模式")
        self.tabs.addTab(self.tree_tab, "事件树模式")
        right_layout.addWidget(self.tabs)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([360, 920])

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

    def _build_interactive_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.event_text = QTextBrowser()
        self.event_text.setPlaceholderText("事件文本将显示在这里")
        self.event_text.setMinimumHeight(220)

        self.reward_hint = QLabel("奖励提示：待解析 JSON 效果")
        self.reward_hint.setWordWrap(True)
        self.reward_hint.setMinimumHeight(60)
        self.reward_hint.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.reward_hint.setTextFormat(Qt.TextFormat.RichText)
        self.reward_hint.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.reward_hint.linkActivated.connect(self.on_effect_link_activated)
        self.reward_hint.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.reward_hint.setStyleSheet(
            """
            QLabel {
                background: #f2f4f8;
                border: 1px solid #d9e1ea;
                border-radius: 8px;
                padding: 10px;
            }
            """
        )

        self.option_container = QWidget()
        self.option_layout = QVBoxLayout(self.option_container)
        self.option_layout.setContentsMargins(0, 0, 0, 0)
        self.option_layout.setSpacing(8)
        self.option_layout.addStretch(1)

        self.option_scroll = QScrollArea()
        self.option_scroll.setWidgetResizable(True)
        self.option_scroll.setFrameShape(QScrollArea.Shape.StyledPanel)
        self.option_scroll.setWidget(self.option_container)

        layout.addWidget(self.event_text, 4)
        layout.addWidget(self.reward_hint, 1)
        layout.addWidget(self.option_scroll, 5)
        return container

    def _build_tree_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        hint = QLabel("树模式：按需展开，点击任意节点可继续在树模式中查看。")
        hint.setStyleSheet("color: #6b7280; padding: 4px 2px;")

        self.tree_text = QTextBrowser()
        self.tree_text.setPlaceholderText("在这里显示选中节点的完整文本与效果（树模式）")
        self.tree_text.setMinimumHeight(140)

        self.tree_reward_hint = QLabel("奖励提示：请选择树中的节点查看奖励内容。")
        self.tree_reward_hint.setWordWrap(True)
        self.tree_reward_hint.setMinimumHeight(60)
        self.tree_reward_hint.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tree_reward_hint.setTextFormat(Qt.TextFormat.RichText)
        self.tree_reward_hint.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.tree_reward_hint.linkActivated.connect(self.on_effect_link_activated)
        self.tree_reward_hint.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tree_reward_hint.setStyleSheet(
            """
            QLabel {
                background: #f2f4f8;
                border: 1px solid #d9e1ea;
                border-radius: 8px;
                padding: 10px;
            }
            """
        )

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setUniformRowHeights(False)
        self.tree_widget.setWordWrap(True)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.itemExpanded.connect(self.on_tree_item_expanded)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)

        layout.addWidget(hint)
        layout.addWidget(self.tree_reward_hint)
        layout.addWidget(self.tree_text)
        layout.addWidget(self.tree_widget, 1)
        return container

    def _load_demo_content(self) -> None:
        try:
            has_db = self.dao.has_nodes()
        except Exception:
            has_db = False

        if not has_db:
            demo_events = [
                "舰船遭遇战 - 例子 1",
                "贸易站事件 - 例子 2",
                "星云异常 - 例子 3",
                "遗迹探索 - 例子 4",
            ]
            self.event_list.addItems(demo_events)

        self.event_text.setHtml(
            "<h2>FTL 事件预览</h2>"
            "<p>左侧搜索后，点击结果即可在交互模式中查看文本与分支。</p>"
            "<p>树模式会按需展开，帮助你快速查看网状剧情结构。</p>"
        )
        self.reward_hint.setText("请选择左侧事件或搜索结果开始浏览。")
