from __future__ import annotations

import json
import logging

from translation_dict import translate


logger = logging.getLogger(__name__)


class EffectsFormatterMixin:
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
            return f" {self._html_escape(text)}"

        def get_value(data, field, default=""):
            if isinstance(data, dict):
                return data.get(field, default)
            return default

        def as_dict(value):
            return value if isinstance(value, dict) else {}

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

                return f"[获得物资] 级别: {self._html_escape(level_text)}, 类型: {self._html_escape(reward_type_text)}"

            if key == "damage":
                amount = get_value(value, "amount", "未知")
                try:
                    amount_int = int(amount)
                except Exception:
                    amount_int = None

                system = get_value(value, "system")
                if amount_int is not None and amount_int < 0:
                    return f"[修复舰体] 修复量: {abs(amount_int)}"
                if system:
                    display_amount = amount_int if amount_int is not None else amount
                    return f"[受到伤害] 伤害量: {self._html_escape(display_amount)}, 损坏系统: {self._html_escape(translate('systems', system))}"
                display_amount = amount_int if amount_int is not None else amount
                return f"[受到伤害] 船体伤害量: {self._html_escape(display_amount)}"

            if key == "crewMember":
                amount = get_value(value, "amount", "未知")
                crew_class = get_value(value, "class", "未知")
                return f"[获得船员] {self._html_escape(amount)}名 {self._html_escape(translate('crew', crew_class))}"

            if key == "weapon":
                weapon_name = get_value(value, "name", "未知")
                return f"[获得武器] {self._html_escape(translate('weapons', weapon_name))}"

            if key == "item_modify":
                items = find_item_modify_items(value)

                lines = []
                for item_data in items:
                    item_dict = item_data if isinstance(item_data, dict) else {}
                    t = translate("rewards", item_dict.get("type", "未知"))
                    min_value = item_dict.get("min", "?")
                    max_value = item_dict.get("max", "?")
                    lines.append(
                        f"[资源修正] {self._html_escape(t)} 最小:{self._html_escape(min_value)} 最大:{self._html_escape(max_value)}"
                    )

                if lines:
                    return "<br>".join(lines)
                return "[资源修正] 未知"

            if key == "reveal_map":
                return "[星图更新] 获得了当前星区的数据。"

            if key == "unlockCustomShip":
                ship_id = get_value(value, "value", "未知")
                ship_req = get_value(value, "shipReq")
                silent = get_value(value, "silent")
                parts = [f"[解锁船只] 解锁船只：{self._html_escape(ship_id)}"]
                if ship_req:
                    parts.append(f"前置船只要求：{self._html_escape(ship_req)}")
                if silent != "":
                    parts.append(f"静默：{self._html_escape(silent)}")
                return ", ".join(parts)

            if key == "achievement":
                achievement_value = get_value(value, "value", "未知")
                achievement_text = translate("achievements", achievement_value)
                return f"[成就解锁] 成就解锁：{self._html_escape(achievement_text)}"

            if key == "upgrade":
                system = get_value(value, "system", "未知")
                amount = get_value(value, "amount", "未知")
                return f"[系统升级] 系统升级：{self._html_escape(translate('systems', system))}上升{self._html_escape(amount)}级"

            if key == "augment":
                augment_name = get_value(value, "name", "未知")
                augment_value = get_value(value, "value", "未知")
                return f"[环境描述] 获得增强部件，名称：{self._html_escape(translate('augment', augment_name))}，值：{self._html_escape(translate('augment', augment_value))}"

            if key == "hiddenAug":
                augment_value = get_value(value, "value", "未知")
                return f"[特殊触发] 内置化部件，名称：{self._html_escape(translate('augment', augment_value))}"

            if key == "modifyPursuit":
                amount = get_value(value, "amount", "0")
                try:
                    amount_int = int(amount)
                except Exception:
                    amount_int = 0
                if amount_int > 0:
                    return f"[舰队追击] 叛军舰队提前 {amount_int} 跳"
                if amount_int < 0:
                    return f"[舰队追击] 叛军舰队被延缓 {abs(amount_int)} 跳"
                return f"[舰队追击] 叛军舰队追击不变：{amount_int} 跳"

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
                return f"[环境变化] 当前环境变为：{self._html_escape(env_name)}"

            if key == "loadEvent":
                target_id = get_value(value, "value", "未知")
                return f"[加载事件] 下一步加载事件：{self._format_load_event_link(target_id)}"

            if key == "quest":
                target = get_value(value, "event", "未知")
                return f"[触发任务] 标记目标事件: {self._html_escape(target)}"

            if key == "removeCrew":
                children = as_dict(value).get("children", {})
                text_dict = as_dict(children).get("text", {})
                msg = as_dict(text_dict).get("value", "失去了一名船员。")
                clone_dict = as_dict(children).get("clone", {})
                can_clone = as_dict(clone_dict).get("value", "true")
                if can_clone == "false":
                    return f"[失去船员] (不可克隆) {self._html_escape(msg)}"
                return f"[失去船员] {self._html_escape(msg)}"

            if key == "boarders":
                min_value = get_value(value, "min", "?")
                max_value = get_value(value, "max", "?")
                crew_class = get_value(value, "class", "未知")
                return f"[遭遇跳帮] {self._html_escape(min_value)}到{self._html_escape(max_value)}名 {self._html_escape(translate('crew', crew_class))} 入侵！"

            if key == "drone":
                name = get_value(value, "name", "未知")
                drone_value = get_value(value, "value", name)
                return f"[特殊触发] 获得无人机，名称：{self._html_escape(translate('drones', name))}，值：{self._html_escape(translate('drones', drone_value))}"

            if key == "remove":
                name = get_value(value, "name", "未知")
                remove_value = get_value(value, "value", name)
                return f"[特殊触发] 失去物品，名称：{self._html_escape(translate('rewards', name))}，值：{self._html_escape(translate('rewards', remove_value))}"

            if key == "ship":
                hostile = get_value(value, "hostile", "true")
                if hostile == "false":
                    return "[特殊触发] [战斗控制] 对方停止开火，变为中立状态"
                return "[特殊触发] [战斗控制] 对方变为敌对状态，开始交战！"

            if key == "clearJumpEvent":
                return f"[特殊触发] 清除事件残留{raw_output(value)}"

            if key == "preventQuest":
                return f"[特殊触发] 阻止信标生成任务{raw_output(value)}"

            if key == "variable":
                name = get_value(value, "name", "未知")
                op = get_value(value, "op", "未知")
                val = get_value(value, "val", "未知")
                return f"[特殊触发] [后台变量] 当前战役状态更新 ({self._html_escape(name)} {self._html_escape(op)} {self._html_escape(val)})"

            if key == "beaconType":
                children = as_dict(value).get("children", {})
                tooltip = as_dict(as_dict(children).get("unvisitedTooltip", {})).get("value")
                if tooltip:
                    return f"[特殊触发] [星图更新] 标记特殊信标：{self._html_escape(tooltip)}"
                return "[特殊触发] [星图更新] 添加了一个特殊的地图标记"

            if key == "preventFleet":
                return "[特殊触发] [舰队追踪] 叛军舰队本回合停止推进"

            if key == "instantEscape":
                return "[特殊触发] [战斗控制] 敌方飞船立即折跃逃跑！"

            if key == "recallBoarders":
                return "[特殊触发] [战斗控制] 强制召回所有登舰人员"

            if key == "eventAlias":
                return f"[特殊触发] [事件重定向] 触发了特殊的隐藏事件分支{raw_output(value)}"

            if key == "metaVariable":
                return f"[特殊触发] 全局元数据更新，直接写入存档等内容{raw_output(value)}"

            if isinstance(value, dict):
                return f"[特殊触发] {self._html_escape(key)}: {self._html_escape(json.dumps(value, ensure_ascii=False))}"
            return f"[特殊触发] {self._html_escape(key)}: {self._html_escape(as_text(value))}"

        lines: list[str] = []
        if isinstance(parsed, dict):
            for key, value in parsed.items():
                lines.append(format_entry(str(key), value))
            return "<br>".join(line for line in lines if line)

        if isinstance(parsed, list):
            for entry in parsed:
                if isinstance(entry, dict) and len(entry) == 1:
                    key, value = next(iter(entry.items()))
                    lines.append(format_entry(str(key), value))
                else:
                    lines.append(f"[特殊触发] {self._html_escape(as_text(entry))}")
            return "<br>".join(line for line in lines if line)

        return self._html_escape(as_text(parsed))
