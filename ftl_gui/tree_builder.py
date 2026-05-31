from __future__ import annotations

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QTreeWidgetItem


class TreeBuilderMixin:
    def _populate_tree_root(self, node_id: str) -> None:
        self.tree_widget.clear()
        try:
            root_path = self._find_tree_root_path(node_id)
            root_id = root_path[0] if root_path else node_id
            row = self.dao.get_node(root_id)
        except Exception:
            row = None

        if not row:
            item = QTreeWidgetItem([f"未找到节点: {node_id}"])
            self.tree_widget.addTopLevelItem(item)
            self.tree_reward_hint.setText("未找到对应节点。")
            self.tree_text.setPlainText(f"未找到节点: {node_id}")
            return

        current_row = self.dao.get_node(node_id)
        if current_row:
            self.tree_text.setPlainText(current_row["text"] or current_row["id"])
            self.tree_reward_hint.setText(self._build_reward_hint(current_row))
        else:
            self.tree_text.setPlainText(row["text"] or row["id"])
            self.tree_reward_hint.setText(self._build_reward_hint(row))

        root_item = self._make_node_item(row, path=(root_id,))
        self.tree_widget.addTopLevelItem(root_item)
        self._load_tree_node_children(root_item, row, path=(root_id,))

        selected_item = self._expand_tree_path_to_target(root_item, root_path)
        self.tree_widget.setCurrentItem(selected_item)
        self.tree_widget.scrollToItem(selected_item)

    def _load_tree_item_children(self, item: QTreeWidgetItem) -> None:
        kind = str(item.data(0, self.ROLE_KIND) or "")
        target_id = str(item.data(0, self.ROLE_TARGET_ID) or "")
        path = self._item_path(item)

        self._clear_tree_children(item)

        if not target_id:
            item.setData(0, self.ROLE_LOADED, True)
            return

        if kind in {"CHOICE", "LIST_ENTRY", "BRANCH"}:
            self._attach_target_node(item, target_id, path)
            item.setData(0, self.ROLE_LOADED, True)
            return

        try:
            row = self.dao.get_node(target_id)
        except Exception:
            row = None

        if not row:
            missing = QTreeWidgetItem([f"未找到节点: {target_id}"])
            missing.setData(0, self.ROLE_TARGET_ID, target_id)
            missing.setData(0, self.ROLE_KIND, "MISSING")
            item.addChild(missing)
            item.setData(0, self.ROLE_LOADED, True)
            return

        self._load_tree_node_children(item, row, path=path)
        item.setData(0, self.ROLE_LOADED, True)

    def _load_tree_node_children(self, parent_item: QTreeWidgetItem, row, path: tuple[str, ...]) -> None:
        node_id = row["id"]
        node_type = row["type"] or ""

        if node_type in {"EVENT", "SHIP", "PLACEHOLDER"}:
            try:
                choices = self.dao.get_choices(node_id)
            except Exception:
                choices = []
            for choice in choices:
                self._add_choice_tree_item(parent_item, choice, path)

            try:
                branches = self.dao.get_branches(node_id)
            except Exception:
                branches = []
            for branch in branches:
                self._add_branch_tree_item(parent_item, branch, path)

        elif node_type in {"EVENT_LIST", "TEXT_LIST"}:
            try:
                entries = self.dao.get_list_entries(node_id)
            except Exception:
                entries = []
            for entry in entries:
                self._add_list_tree_item(parent_item, entry, path)

        parent_item.setData(0, self.ROLE_LOADED, True)

    def _add_choice_tree_item(self, parent_item: QTreeWidgetItem, choice, path: tuple[str, ...]) -> None:
        next_id = choice["next_node_id"]
        if not next_id:
            return

        label = self._choice_tree_label(choice)
        choice_item = QTreeWidgetItem([label])
        choice_item.setData(0, self.ROLE_TARGET_ID, next_id)
        choice_item.setData(0, self.ROLE_KIND, "CHOICE")
        choice_item.setData(0, self.ROLE_PATH, path)
        choice_item.setToolTip(0, self._choice_tooltip(choice))

        if next_id in path:
            self._mark_cycle_item(choice_item, next_id)
        else:
            self._add_placeholder_child(choice_item)

        parent_item.addChild(choice_item)

    def _add_list_tree_item(self, parent_item: QTreeWidgetItem, entry, path: tuple[str, ...]) -> None:
        child_id = entry["child_node_id"]
        if not child_id:
            return

        label = f"🎲 随机分支 -> [{child_id}]"
        entry_item = QTreeWidgetItem([label])
        entry_item.setData(0, self.ROLE_TARGET_ID, child_id)
        entry_item.setData(0, self.ROLE_KIND, "LIST_ENTRY")
        entry_item.setData(0, self.ROLE_PATH, path)
        entry_item.setToolTip(0, self._list_entry_tooltip(entry))

        if child_id in path:
            self._mark_cycle_item(entry_item, child_id)
        else:
            self._add_placeholder_child(entry_item)

        parent_item.addChild(entry_item)

    def _add_branch_tree_item(self, parent_item: QTreeWidgetItem, branch, path: tuple[str, ...]) -> None:
        next_id = branch["next_node_id"]
        if not next_id:
            return

        ship_name = branch["ship_name"] or ""
        prefix = f"{ship_name} " if ship_name else ""
        label = f"⚔️ {prefix}[{branch['branch_type']}] -> [{next_id}]"
        branch_item = QTreeWidgetItem([label])
        branch_item.setData(0, self.ROLE_TARGET_ID, next_id)
        branch_item.setData(0, self.ROLE_KIND, "BRANCH")
        branch_item.setData(0, self.ROLE_PATH, path)
        branch_item.setToolTip(0, self._branch_tooltip(branch))

        if next_id in path:
            self._mark_cycle_item(branch_item, next_id)
        else:
            self._add_placeholder_child(branch_item)

        parent_item.addChild(branch_item)

    def _attach_target_node(self, parent_item: QTreeWidgetItem, target_id: str, path: tuple[str, ...]) -> None:
        try:
            row = self.dao.get_node(target_id)
        except Exception:
            row = None

        if not row:
            missing = QTreeWidgetItem([f"未找到节点: {target_id}"])
            missing.setData(0, self.ROLE_TARGET_ID, target_id)
            missing.setData(0, self.ROLE_KIND, "MISSING")
            parent_item.addChild(missing)
            return

        if target_id in path:
            cycle_item = QTreeWidgetItem([f"🔄 [循环返回至: {target_id}]"])
            cycle_item.setData(0, self.ROLE_TARGET_ID, target_id)
            cycle_item.setData(0, self.ROLE_KIND, "CYCLE")
            cycle_item.setData(0, self.ROLE_PATH, path)
            cycle_item.setForeground(0, QBrush(QColor("#b00020")))
            cycle_item.setToolTip(0, self._build_node_tooltip(row, cycle=True))
            parent_item.addChild(cycle_item)
            return

        new_path = path + (target_id,) if not path or path[-1] != target_id else path
        child_item = self._make_node_item(row, new_path)
        self._add_placeholder_child(child_item)
        parent_item.addChild(child_item)

    def _populate_node_children_for_item(self, item: QTreeWidgetItem, row) -> None:
        self._clear_tree_children(item)
        path = self._item_path(item)
        self._load_tree_node_children(item, row, path=path)

    def _make_node_item(self, row, path: tuple[str, ...]) -> QTreeWidgetItem:
        node_type = row["type"] or ""
        icon = self._node_icon(node_type)
        preview = self._preview_text(row["text"] or row["id"], 15)
        label = f"{icon} {row['id']} - {preview}"
        item = QTreeWidgetItem([label])
        item.setData(0, self.ROLE_TARGET_ID, row["id"])
        item.setData(0, self.ROLE_KIND, node_type)
        item.setData(0, self.ROLE_PATH, path)
        item.setData(0, self.ROLE_LOADED, False)
        item.setToolTip(0, self._build_node_tooltip(row))
        return item

    def _add_placeholder_child(self, item: QTreeWidgetItem) -> None:
        placeholder = QTreeWidgetItem(["加载中..."])
        placeholder.setData(0, self.ROLE_KIND, "PLACEHOLDER")
        item.addChild(placeholder)

    def _mark_cycle_item(self, item: QTreeWidgetItem, target_id: str) -> None:
        item.setText(0, f"🔄 [循环返回至: {target_id}]")
        item.setForeground(0, QBrush(QColor("#b00020")))

    def _clear_tree_children(self, item: QTreeWidgetItem) -> None:
        while item.childCount():
            item.takeChild(0)
