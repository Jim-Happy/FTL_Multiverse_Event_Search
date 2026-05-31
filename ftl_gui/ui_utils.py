from __future__ import annotations

import html
import re

from translation_dict import translate


class UIUtilsMixin:
    def _tree_node_id_display(self, node_id: str) -> str:
        clean = (node_id or "").strip()
        if len(clean) <= 5:
            return clean.rstrip("_")
        return clean[:5].rstrip("_")

    def _preview_text(self, text: str, limit: int = 15) -> str:
        clean = (text or "").replace("\n", " ").strip()
        if len(clean) <= limit:
            return clean
        return clean[:limit] + "..."

    def _html_escape(self, value) -> str:
        return html.escape("") if value is None else html.escape(str(value))

    def _format_load_event_link(self, event_id: str) -> str:
        safe_event_id = self._html_escape(event_id)
        return f'<a href="loadEvent:{safe_event_id}">{safe_event_id}</a>'

    def _translate_requirement(self, raw_key: str) -> str:
        if not raw_key:
            return ""

        translated = translate("systems", raw_key)
        if translated != raw_key:
            return translated

        translated = translate("crew", raw_key)
        if translated != raw_key:
            return translated

        return raw_key

    def _choice_button_text(self, choice) -> str:
        choice_text = choice["text"] or "(无文本)"
        req = choice["req"] or ""
        req_text = self._translate_requirement(req)
        prefix = f"[需求: {req_text}] " if req_text else ""
        return f"{prefix}{choice_text}"

    def _choice_tree_label(self, choice) -> str:
        next_id = choice["next_node_id"] or ""
        return f"➡️ {self._choice_button_text(choice)} -> [{next_id}]"

    def _html_to_plain_text(self, value: str) -> str:
        clean = value.replace("<br>", "\n")
        clean = re.sub(r"<[^>]+>", "", clean)
        return html.unescape(clean)

    def _build_tree_node_html(self, row) -> str:
        node_type = row["type"] or ""
        icon = self._node_icon(node_type)
        display_id = self._tree_node_id_display(row["id"])
        display_text = (row["text"] or "").strip()
        title = f"{icon} {display_id} - {display_text}" if display_text else f"{icon} {display_id}"

        parts = [f'<span style="font-weight: 600;">{self._html_escape(title)}</span>']
        effects_json = row["effects_json"] or ""
        if effects_json:
            reward_html = self.format_effects_json(effects_json)
            if reward_html and reward_html != "效果: 无":
                filtered_lines = [line for line in reward_html.split("<br>") if "[特殊触发]" not in line]
                if filtered_lines:
                    parts.append("<br>".join(filtered_lines))
        return "<br>".join(parts)

    def _node_icon(self, node_type: str) -> str:
        icon_map = {
            "EVENT": "📄",
            "EVENT_LIST": "🎲",
            "TEXT_LIST": "🎲",
            "SHIP": "⚔️",
            "PLACEHOLDER": "📄",
        }
        return icon_map.get(node_type, "📄")

    def _build_reward_hint(self, row) -> str:
        parts = [f"类型: {self._html_escape(row['type'] or '')}", f"ID: {self._html_escape(row['id'])}"]
        effects_json = row["effects_json"] or ""
        if effects_json:
            parts.append(self.format_effects_json(effects_json))
        return "<br>".join(parts)

    def _build_node_tooltip(self, row, cycle: bool = False) -> str:
        lines = [
            f"ID: {row['id']}",
            f"类型: {row['type'] or ''}",
            f"文本: {row['text'] or ''}",
        ]
        if row["effects_json"]:
            lines.append(f"effects: {row['effects_json']}")
        if cycle:
            lines.append("循环节点：继续展开会回到当前路径中的节点。")
        return "\n".join(lines)

    def _choice_tooltip(self, choice) -> str:
        lines = [
            f"Choice ID: {choice['id']}",
            f"文本: {choice['text'] or ''}",
            f"需求: {choice['req'] or ''}",
            f"hidden: {choice['is_hidden']}",
            f"blue: {choice['is_blue']}",
            f"next: {choice['next_node_id'] or ''}",
        ]
        return "\n".join(lines)

    def _list_entry_tooltip(self, entry) -> str:
        return f"ListEntry ID: {entry['id']}\nlist: {entry['list_node_id']}\nchild: {entry['child_node_id']}"

    def _branch_tooltip(self, branch) -> str:
        lines = [
            f"Branch ID: {branch['id']}",
            f"parent: {branch['parent_node_id']}",
            f"ship: {branch['ship_name'] or ''}",
            f"type: {branch['branch_type']}",
            f"next: {branch['next_node_id']}",
        ]
        if branch["branch_json"]:
            lines.append(f"json: {branch['branch_json']}")
        return "\n".join(lines)
