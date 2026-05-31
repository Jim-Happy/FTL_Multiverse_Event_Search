from __future__ import annotations

from functools import partial

from PyQt6.QtWidgets import QLabel, QPushButton


class NodeRendererMixin:
    def render_node(self, node_id: str, sync_tree: bool = True) -> None:
        if not node_id:
            return

        try:
            row = self.dao.get_node(node_id)
        except Exception:
            row = None

        if not row:
            self.event_text.setPlainText(f"未找到节点: {node_id}")
            self.reward_hint.setText("未找到对应节点。")
            self._clear_option_area()
            if sync_tree:
                self.tree_widget.clear()
            self.tabs.setCurrentWidget(self.interactive_tab)
            return

        self.event_text.setPlainText(row["text"] or row["id"])
        self.reward_hint.setText(self._build_reward_hint(row))
        self._clear_option_area()

        node_type = row["type"] or ""
        handlers_added = 0

        if node_type in {"EVENT", "SHIP", "PLACEHOLDER"}:
            handlers_added += self._add_choice_buttons(node_id)
            handlers_added += self._add_branch_buttons(node_id)
        elif node_type in {"EVENT_LIST", "TEXT_LIST"}:
            handlers_added += self._add_list_entry_buttons(node_id)

        if handlers_added == 0:
            notice = QLabel("没有可用的下一步。")
            notice.setStyleSheet("color: #6b7280; padding: 6px 2px;")
            self.option_layout.addWidget(notice)

        self.option_layout.addStretch(1)

        if sync_tree:
            self._populate_tree_root(node_id)

        if sync_tree:
            self.tabs.setCurrentWidget(self.interactive_tab)

    def _clear_option_area(self) -> None:
        while self.option_layout.count():
            item = self.option_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)

    def _add_choice_buttons(self, node_id: str) -> int:
        try:
            choices = self.dao.get_choices(node_id)
        except Exception:
            choices = []

        count = 0
        for choice in choices:
            display = self._choice_button_text(choice)
            next_id = choice["next_node_id"]
            if not next_id:
                continue
            btn = QPushButton(display)
            btn.clicked.connect(partial(self.render_node, next_id, True))
            self.option_layout.addWidget(btn)
            count += 1
        return count

    def _add_list_entry_buttons(self, node_id: str) -> int:
        try:
            entries = self.dao.get_list_entries(node_id)
        except Exception:
            entries = []

        count = 0
        for entry in entries:
            child_id = entry["child_node_id"]
            if not child_id:
                continue
            btn = QPushButton(f"随机分支 -> [{child_id}]")
            btn.clicked.connect(partial(self.render_node, child_id, True))
            self.option_layout.addWidget(btn)
            count += 1
        return count

    def _add_branch_buttons(self, node_id: str) -> int:
        try:
            branches = self.dao.get_branches(node_id)
        except Exception:
            branches = []

        count = 0
        for branch in branches:
            next_id = branch["next_node_id"]
            if not next_id:
                continue
            ship_name = branch["ship_name"] or ""
            prefix = f"{ship_name} " if ship_name else ""
            btn = QPushButton(f"⚔️ {prefix}[{branch['branch_type']}] -> [{next_id}]")
            btn.clicked.connect(partial(self.render_node, next_id, True))
            self.option_layout.addWidget(btn)
            count += 1
        return count
