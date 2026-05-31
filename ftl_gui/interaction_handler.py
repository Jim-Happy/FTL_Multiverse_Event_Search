from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem, QTreeWidgetItem


class InteractionHandlerMixin:
    def on_search(self) -> None:
        keyword = self.search_input.text().strip()
        if not keyword:
            self.event_list.clear()
            return

        try:
            results = self.dao.search_nodes(keyword)
        except Exception:
            self.event_list.clear()
            return

        self.event_list.clear()
        for node_id, node_text in results:
            snippet = node_id if len(node_id) <= 40 else node_id[:37] + "..."
            text_preview = self._preview_text(node_text, 15)
            display = f"文本: {text_preview} | ID: {snippet}"
            if node_text and len(node_text) > 15:
                display += "..."
            item = QListWidgetItem(display)
            item.setToolTip(node_id)
            item.setData(Qt.ItemDataRole.UserRole, node_id)
            self.event_list.addItem(item)

        if self.event_list.count():
            self.event_list.setCurrentRow(0)

    def on_event_list_current_item_changed(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        del previous
        if current is None:
            return

        node_id = current.data(Qt.ItemDataRole.UserRole)
        if not node_id:
            return

        if self.tabs.currentWidget() is self.tree_tab:
            self._populate_tree_root(str(node_id))
            return

        self.render_node(str(node_id), sync_tree=True)

    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        del column
        target_id = item.data(0, self.ROLE_TARGET_ID)
        if not target_id:
            return

        try:
            row = self.dao.get_node(str(target_id))
        except Exception:
            row = None

        if row:
            self.tree_text.setPlainText(row["text"] or "")
            self.tree_reward_hint.setText(self._build_reward_hint(row))
        else:
            self.tree_text.setPlainText(f"未找到节点: {target_id}")
            self.tree_reward_hint.setText("未找到对应节点。")

        self.render_node(str(target_id), sync_tree=False)

    def on_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.data(0, self.ROLE_LOADED):
            return
        self._load_tree_item_children(item)

    def on_effect_link_activated(self, link: str) -> None:
        if not link.startswith("loadEvent:"):
            return

        target_id = link.split(":", 1)[1].strip()
        if not target_id:
            return

        if self.tabs.currentWidget() is self.tree_tab:
            self._populate_tree_root(target_id)
            return

        self.search_input.setText(target_id)
        self.search_input.setFocus()
        self.on_search()
