from __future__ import annotations

from PyQt6.QtWidgets import QTreeWidgetItem


class TreeNavigationMixin:
    def _find_tree_root_path(self, node_id: str) -> list[str]:
        visited: set[str] = set()

        def walk(current_id: str, active_path: set[str]) -> list[str]:
            if current_id in active_path:
                return [current_id]

            parents = self.dao.get_parent_links(current_id)
            if not parents:
                return [current_id]

            next_active_path = set(active_path)
            next_active_path.add(current_id)

            for link in parents:
                parent_id = str(link["parent_id"] or "")
                if not parent_id or parent_id in visited:
                    continue
                visited.add(parent_id)
                path = walk(parent_id, next_active_path)
                if path:
                    return path + [current_id]

            return [current_id]

        return walk(node_id, set())

    def _find_direct_tree_child_by_target(self, parent_item: QTreeWidgetItem, target_id: str) -> QTreeWidgetItem | None:
        for index in range(parent_item.childCount()):
            child_item = parent_item.child(index)
            if str(child_item.data(0, self.ROLE_TARGET_ID) or "") == target_id:
                return child_item
        return None

    def _expand_tree_path_to_target(self, root_item: QTreeWidgetItem, path: list[str]) -> QTreeWidgetItem:
        current_item = root_item
        for target_id in path[1:]:
            if not current_item.data(0, self.ROLE_LOADED):
                self._load_tree_item_children(current_item)
            current_item.setExpanded(True)

            next_item = self._find_direct_tree_child_by_target(current_item, target_id)
            if next_item is None:
                self._load_tree_item_children(current_item)
                next_item = self._find_direct_tree_child_by_target(current_item, target_id)
            if next_item is None:
                return current_item

            kind = str(next_item.data(0, self.ROLE_KIND) or "")
            if kind in {"CHOICE", "LIST_ENTRY", "BRANCH"}:
                if not next_item.data(0, self.ROLE_LOADED):
                    self._load_tree_item_children(next_item)
                next_item.setExpanded(True)
                node_item = self._find_direct_tree_child_by_target(next_item, target_id)
                if node_item is not None:
                    next_item = node_item

            current_item = next_item

        if not current_item.data(0, self.ROLE_LOADED):
            self._load_tree_item_children(current_item)
        current_item.setExpanded(True)
        return current_item

    def _item_path(self, item: QTreeWidgetItem) -> tuple[str, ...]:
        path_value = item.data(0, self.ROLE_PATH)
        if isinstance(path_value, tuple):
            return path_value
        if isinstance(path_value, list):
            return tuple(str(value) for value in path_value)
        if path_value:
            return (str(path_value),)
        return tuple()
