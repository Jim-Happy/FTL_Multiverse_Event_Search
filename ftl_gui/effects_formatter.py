from __future__ import annotations

import html
import json
import logging
import re

from translation_dict import translate


logger = logging.getLogger(__name__)


class EffectsFormatterMixin:
    def _highlight_effect_tags(self, html_text: str) -> str:
        if not html_text:
            return html_text

        tag_colors = {
            "获得物资": "#0f766e",
            "修复舰体": "#16a34a",
            "受到伤害": "#dc2626",
            "获得船员": "#2563eb",
            "获得武器": "#7c3aed",
            "资源修正": "#d97706",
            "星图更新": "#0284c7",
            "解锁船只": "#0891b2",
            "成就解锁": "#9333ea",
            "系统升级": "#2563eb",
            "环境描述": "#0f766e",
            "特殊触发": "#64748b",
            "获得内置部件": "#0f766e",
            "舰队追击": "#ea580c",
            "环境变化": "#0ea5e9",
            "加载事件": "#4f46e5",
            "触发任务": "#a16207",
            "失去船员": "#b91c1c",
            "遭遇跳帮": "#be123c",
            "获得无人机": "#0f766e",
            "失去物品": "#dc2626",
            "战斗控制": "#dc2626",
            "后台变量": "#6b7280",
            "事件重定向": "#7c3aed",
        }

        def repl(match: re.Match[str]) -> str:
            label = match.group(0)
            tag_name = label[1:-1]
            color = tag_colors.get(tag_name, "#475569")
            return f'<span style="color:{color}; font-weight:700;">{html.escape(label)}</span>'

        return "<br>".join(re.sub(r"\[[^\]]+\]", repl, line) for line in html_text.split("<br>"))

    def format_effects_json(self, json_str):
        if not json_str:
            return "效果: 无"

        try:
            parsed = json.loads(json_str) if isinstance(json_str, str) else json_str
        except Exception:
            return f"效果: {json_str}"

        if not parsed:
            return "效果: 无"

        def as_text(value) -> str:
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

        def raw_output(value) -> str:
            text = as_text(value)
            if not text:
                return ""
            return f" {html.escape(text)}"

        def get_value(data, field, default=""):
            if isinstance(data, dict):
                return data.get(field, default)
            return default

        def as_dict(value):
            return value if isinstance(value, dict) else {}

        def escape(value) -> str:
            return html.escape("") if value is None else html.escape(str(value))

        def tagged(label: str, body: str = "", color: str = "#475569") -> str:
            return f'<span style="color:{color}; font-weight:700;">{escape(label)}</span>{body}'

        tag_styles = {
            "[获得物资]": "#0f766e",
            "[修复舰体]": "#16a34a",
            "[受到伤害]": "#dc2626",
            "[获得船员]": "#2563eb",
            "[获得武器]": "#7c3aed",
            "[资源修正]": "#d97706",
            "[星图更新]": "#0284c7",
            "[解锁船只]": "#0891b2",
            "[成就解锁]": "#9333ea",
            "[系统升级]": "#2563eb",
            "[环境描述]": "#0f766e",
            "[特殊触发]": "#64748b",
            "[舰队追击]": "#ea580c",
            "[环境变化]": "#0ea5e9",
            "[加载事件]": "#4f46e5",
            "[触发任务]": "#a16207",
            "[失去船员]": "#b91c1c",
            "[遭遇跳帮]": "#be123c",
            "[获得无人机]": "#0f766e",
            "[失去物品]": "#dc2626",
            "[战斗控制]": "#dc2626",
            "[后台变量]": "#6b7280",
            "[事件重定向]": "#7c3aed",
        }

        def tag(label: str, body: str = "") -> str:
            return tagged(label, body, tag_styles.get(label, "#475569"))

        def find_item_modify_items(value):
            candidates = [
                value,
                as_dict(value).get("item"),
                as_dict(as_dict(value).get("children")).get("item"),
            ]
            for candidate in candidates:
                if isinstance(candidate, list):
                    return [item for item in candidate if isinstance(item, dict)]
                candidate_dict = as_dict(candidate)
                if any(key in candidate_dict for key in ("type", "min", "max")):
                    return [candidate_dict]
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            return []

        def format_entry(key: str, value) -> str:
            if key == "autoReward":
                level = get_value(value, "level", "未知")
                reward_type = get_value(value, "type") or get_value(value, "value", "未知")
                level_text = translate("rewards", level)
                reward_type_text = translate("rewards", reward_type)

                if level_text == "未知" or reward_type_text == "未知":
                    logger.warning(
                        "Unresolved autoReward mapping. level=%r, type=%r, translated_level=%r, translated_type=%r, payload=%s",
                        level,
                        reward_type,
                        level_text,
                        reward_type_text,
                        json.dumps(value, ensure_ascii=False),
                    )

                return tag("[获得物资]", f" 级别: {escape(level_text)}, 类型: {escape(reward_type_text)}")

            if key == "damage":
                amount = get_value(value, "amount", "未知")
                try:
                    amount_int = int(amount)
                except Exception:
                    amount_int = None

                system = get_value(value, "system")
                if amount_int is not None and amount_int < 0:
                    return tag("[修复舰体]", f" 修复量: {abs(amount_int)}")
                if system:
                    display_amount = amount_int if amount_int is not None else amount
                    return tag("[受到伤害]", f" 伤害量: {escape(display_amount)}, 损坏系统: {escape(translate('systems', system))}")
                display_amount = amount_int if amount_int is not None else amount
                return tag("[受到伤害]", f" 船体伤害量: {escape(display_amount)}")

            if key == "crewMember":
                amount = get_value(value, "amount", "未知")
                crew_class = get_value(value, "class", "未知")
                return tag("[获得船员]", f" {escape(amount)}名 {escape(translate('crew', crew_class))}")

            if key == "weapon":
                weapon_name = get_value(value, "name", "未知")
                return tag("[获得武器]", f" {escape(translate('weapons', weapon_name))}")

            if key == "item_modify":
                items = find_item_modify_items(value)

                lines = []
                for item_data in items:
                    item_dict = item_data if isinstance(item_data, dict) else {}
                    t = translate("rewards", item_dict.get("type", "未知"))
                    min_value = item_dict.get("min", "?")
                    max_value = item_dict.get("max", "?")
                    lines.append(
                        tag("[资源修正]", f" {escape(t)} 最小:{escape(min_value)} 最大:{escape(max_value)}")
                    )

                if lines:
                    return "<br>".join(lines)
                return tag("[资源修正]", " 未知")

            if key == "reveal_map":
                return tag("[星图更新]", " 获得了当前星区的数据。")

            if key == "unlockCustomShip":
                ship_id = get_value(value, "value", "未知")
                ship_req = get_value(value, "shipReq")
                silent = get_value(value, "silent")
                parts = [tag("[解锁船只]", f" 解锁船只：{escape(ship_id)}")]
                if ship_req:
                    parts.append(f"前置船只要求：{escape(ship_req)}")
                if silent != "":
                    parts.append(f"静默：{escape(silent)}")
                return ", ".join(parts)

            if key == "achievement":
                achievement_value = get_value(value, "value", "未知")
                achievement_text = translate("achievements", achievement_value)
                return tag("[成就解锁]", f" 成就解锁：{escape(achievement_text)}")

            if key == "upgrade":
                system = get_value(value, "system", "未知")
                amount = get_value(value, "amount", "未知")
                return tag("[系统升级]", f" 系统升级：{escape(translate('systems', system))}上升{escape(amount)}级")

            if key == "augment":
                augment_name = get_value(value, "name", "未知")
                augment_value = get_value(value, "value", "未知")
                return tag("[环境描述]", f" 获得增强部件，名称：{escape(translate('augment', augment_name))}，值：{escape(translate('augment', augment_value))}")

            if key == "hiddenAug":
                augment_value = get_value(value, "value", "未知")
                return tag("[获得内置部件]", f" 内置化部件，名称：{escape(translate('augment', augment_value))}")

            if key == "modifyPursuit":
                amount = get_value(value, "amount", "0")
                try:
                    amount_int = int(amount)
                except Exception:
                    amount_int = 0
                if amount_int > 0:
                    return tag("[舰队追击]", f" 叛军舰队提前 {amount_int} 跳")
                if amount_int < 0:
                    return tag("[舰队追击]", f" 叛军舰队被延缓 {abs(amount_int)} 跳")
                return tag("[舰队追击]", f" 叛军舰队追击不变：{amount_int} 跳")

            if key == "environment":
                env_type = get_value(value, "type", "未知")
                env_map = {
                    "asteroid": "小行星场",
                    "sun": "巨型恒星",
                    "pulsar": "脉冲星",
                    "storm": "离子风暴",
                    "nebula": "星云",
                }
                env_name = env_map.get(env_type, env_type)
                return tag("[环境变化]", f" 当前环境变为：{escape(env_name)}")

            if key == "loadEvent":
                target_id = get_value(value, "value", "未知")
                safe_target_id = escape(target_id)
                return tag("[加载事件]", f' 下一步加载事件：<a href="loadEvent:{safe_target_id}">{safe_target_id}</a>')

            if key == "quest":
                target = get_value(value, "event", "未知")
                return tag("[触发任务]", f" 标记目标事件: {escape(target)}")

            if key == "removeCrew":
                children = as_dict(value).get("children", {})
                text_dict = as_dict(children).get("text", {})
                msg = as_dict(text_dict).get("value", "失去了一名船员。")
                clone_dict = as_dict(children).get("clone", {})
                can_clone = as_dict(clone_dict).get("value", "true")
                if can_clone == "false":
                    return tag("[失去船员]", f" (不可克隆) {escape(msg)}")
                return tag("[失去船员]", f" {escape(msg)}")

            if key == "boarders":
                min_value = get_value(value, "min", "?")
                max_value = get_value(value, "max", "?")
                crew_class = get_value(value, "class", "未知")
                return tag("[遭遇跳帮]", f" {escape(min_value)}到{escape(max_value)}名 {escape(translate('crew', crew_class))} 入侵！")

            if key == "drone":
                name = get_value(value, "name", "未知")
                drone_value = get_value(value, "value", name)
                return tag("[获得无人机]", f" 名称：{escape(translate('drones', name))}，值：{escape(translate('drones', drone_value))}")

            if key == "remove":
                name = get_value(value, "name", "未知")
                remove_value = get_value(value, "value", name)
                return tag("[失去物品]", f" 名称：{escape(translate('rewards', name))}，值：{escape(translate('rewards', remove_value))}")

            if key == "ship":
                hostile = get_value(value, "hostile", "true")
                if hostile == "false":
                    return tag("[战斗控制]", " 对方停止开火，变为中立状态")
                return tag("[战斗控制]", " 对方变为敌对状态，开始交战！")

            if key == "clearJumpEvent":
                return tag("[特殊触发]", f" 清除事件残留{raw_output(value)}")

            if key == "preventQuest":
                return tag("[特殊触发]", f" 阻止信标生成任务{raw_output(value)}")

            if key == "variable":
                name = get_value(value, "name", "未知")
                op = get_value(value, "op", "未知")
                val = get_value(value, "val", "未知")
                return tag("[后台变量]", f" 当前战役状态更新 ({escape(name)} {escape(op)} {escape(val)})")

            if key == "beaconType":
                children = as_dict(value).get("children", {})
                tooltip = as_dict(as_dict(children).get("unvisitedTooltip", {})).get("value")
                if tooltip:
                    return tag("[星图更新]", f" 标记特殊信标：{escape(tooltip)}")
                return tag("[星图更新]", " 添加了一个特殊的地图标记")

            if key == "preventFleet":
                return tag("[舰队追击]", " 叛军舰队本回合停止推进")

            if key == "instantEscape":
                return tag("[战斗控制]", " 敌方飞船立即折跃逃跑！")

            if key == "recallBoarders":
                return tag("[战斗控制]", " 强制召回所有登舰人员")

            if key == "eventAlias":
                return tag("[事件重定向]", f" 触发了特殊的隐藏事件分支{raw_output(value)}")

            if key == "metaVariable":
                return tag("[特殊触发]", f" 全局元数据更新，直接写入存档等内容{raw_output(value)}")

            if isinstance(value, dict):
                return tag("[特殊触发]", f" {escape(key)}: {escape(json.dumps(value, ensure_ascii=False))}")
            return tag("[特殊触发]", f" {escape(key)}: {escape(as_text(value))}")

        lines: list[str] = []
        if isinstance(parsed, dict):
            for key, value in parsed.items():
                lines.append(format_entry(str(key), value))
            return self._highlight_effect_tags("<br>".join(line for line in lines if line))

        if isinstance(parsed, list):
            for entry in parsed:
                if isinstance(entry, dict) and len(entry) == 1:
                    key, value = next(iter(entry.items()))
                    lines.append(format_entry(str(key), value))
                else:
                    lines.append(f"[特殊触发] {escape(as_text(entry))}")
            return self._highlight_effect_tags("<br>".join(line for line in lines if line))

        return escape(as_text(parsed))
