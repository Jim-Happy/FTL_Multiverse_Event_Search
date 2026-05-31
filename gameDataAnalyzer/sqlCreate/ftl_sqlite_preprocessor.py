from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any


NODE_TYPES = {"EVENT", "EVENT_LIST", "TEXT_LIST", "SHIP", "TEXT_ENTRY", "PLACEHOLDER"}
BRANCH_TYPES = {"destroyed", "deadCrew", "deadCrewAuto", "surrender", "escape", "gotaway"}


def truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no"}


def local_name(tag: Any) -> str:
    if isinstance(tag, str):
        return tag
    return ""


def has_element_children(elem: ET.Element) -> bool:
    for child in elem:
        if isinstance(child.tag, str):
            return True
    return False


def direct_text_value(elem: ET.Element) -> str | None:
    if elem.text and elem.text.strip():
        return elem.text.strip()

    for key in ("load", "id", "name", "text"):
        value = elem.attrib.get(key)
        if value:
            return value.strip()

    return None


def pack_element(elem: ET.Element) -> Any:
    payload: dict[str, Any] = {}
    for key, value in elem.attrib.items():
        payload[key] = value

    value = direct_text_value(elem)
    if value is not None:
        payload["value"] = value

    grouped_children: dict[str, list[Any]] = defaultdict(list)
    for child in elem:
        if not isinstance(child.tag, str):
            continue
        grouped_children[child.tag].append(pack_element(child))

    if grouped_children:
        payload["children"] = {
            tag: items[0] if len(items) == 1 else items for tag, items in grouped_children.items()
        }

    if not payload:
        return {"value": True}

    return payload


def append_payload(container: dict[str, Any], tag: str, value: Any) -> None:
    if tag not in container:
        container[tag] = value
        return

    existing = container[tag]
    if isinstance(existing, list):
        existing.append(value)
    else:
        container[tag] = [existing, value]


def merge_json_values(existing: Any, new_value: Any) -> Any:
    if existing is None:
        return new_value
    if new_value is None:
        return existing
    if isinstance(existing, dict) and isinstance(new_value, dict):
        merged = dict(existing)
        for key, value in new_value.items():
            if key not in merged:
                merged[key] = value
                continue
            merged[key] = merge_json_values(merged[key], value)
        return merged
    if existing == new_value:
        return existing
    if isinstance(existing, list):
        return existing + [new_value]
    return [existing, new_value]


class FTLSQLitePreprocessor:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self._create_schema()
        self._file_count = 0
        self._ignored_root_count = 0
        self._parse_error_count = 0
        self._node_insert_count = 0
        self._choice_insert_count = 0
        self._list_entry_count = 0
        self._branch_insert_count = 0

    def close(self) -> None:
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS Nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL CHECK (type IN ('EVENT', 'EVENT_LIST', 'TEXT_LIST', 'SHIP', 'TEXT_ENTRY', 'PLACEHOLDER')),
                text TEXT,
                is_unique INTEGER NOT NULL DEFAULT 0,
                effects_json TEXT
            );

            CREATE TABLE IF NOT EXISTS Choices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_node_id TEXT NOT NULL,
                text TEXT,
                req TEXT,
                req_lvl INTEGER,
                req_max_lvl INTEGER,
                is_hidden INTEGER NOT NULL DEFAULT 0,
                is_blue INTEGER NOT NULL DEFAULT 0,
                next_node_id TEXT,
                meta_json TEXT,
                FOREIGN KEY(parent_node_id) REFERENCES Nodes(id),
                FOREIGN KEY(next_node_id) REFERENCES Nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_choices_parent_node_id ON Choices(parent_node_id);
            CREATE INDEX IF NOT EXISTS idx_choices_next_node_id ON Choices(next_node_id);

            CREATE TABLE IF NOT EXISTS List_Entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_node_id TEXT NOT NULL,
                child_node_id TEXT NOT NULL,
                weight INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(list_node_id) REFERENCES Nodes(id),
                FOREIGN KEY(child_node_id) REFERENCES Nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_list_entries_list_node_id ON List_Entries(list_node_id);
            CREATE INDEX IF NOT EXISTS idx_list_entries_child_node_id ON List_Entries(child_node_id);

            CREATE TABLE IF NOT EXISTS Combat_Branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_node_id TEXT NOT NULL,
                ship_name TEXT,
                branch_type TEXT NOT NULL CHECK (branch_type IN ('destroyed', 'deadCrew', 'deadCrewAuto', 'surrender', 'escape', 'gotaway')),
                next_node_id TEXT NOT NULL,
                branch_json TEXT,
                FOREIGN KEY(parent_node_id) REFERENCES Nodes(id),
                FOREIGN KEY(next_node_id) REFERENCES Nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_branches_parent_node_id ON Combat_Branches(parent_node_id);
            CREATE INDEX IF NOT EXISTS idx_branches_next_node_id ON Combat_Branches(next_node_id);
            """
        )

    def ensure_placeholder_node(self, node_id: str) -> None:
        self.upsert_node(node_id=node_id, node_type="PLACEHOLDER")

    def upsert_node(
        self,
        node_id: str,
        node_type: str,
        text: str | None = None,
        is_unique: bool = False,
        effects: dict[str, Any] | None = None,
    ) -> None:
        if node_type not in NODE_TYPES:
            raise ValueError(f"Unsupported node type: {node_type}")

        effects_json = None
        if effects:
            existing_effects_json = self.conn.execute(
                "SELECT effects_json FROM Nodes WHERE id = ?",
                (node_id,),
            ).fetchone()
            if existing_effects_json and existing_effects_json[0]:
                try:
                    existing_effects = json.loads(existing_effects_json[0])
                except json.JSONDecodeError:
                    existing_effects = None
                merged_effects = merge_json_values(existing_effects, effects)
                effects_json = json.dumps(merged_effects, ensure_ascii=False)
            else:
                effects_json = json.dumps(effects, ensure_ascii=False)

        self.conn.execute(
            """
            INSERT INTO Nodes (id, type, text, is_unique, effects_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                type = CASE
                    WHEN Nodes.type = 'PLACEHOLDER' THEN excluded.type
                    WHEN excluded.type = 'PLACEHOLDER' THEN Nodes.type
                    ELSE Nodes.type
                END,
                text = COALESCE(excluded.text, Nodes.text),
                is_unique = CASE
                    WHEN excluded.is_unique IS NULL THEN Nodes.is_unique
                    ELSE excluded.is_unique
                END,
                effects_json = COALESCE(excluded.effects_json, Nodes.effects_json)
            """,
            (node_id, node_type, text, int(is_unique), effects_json),
        )
        self._node_insert_count += 1

    def add_choice(
        self,
        parent_node_id: str,
        text: str | None,
        req: str | None,
        req_lvl: int | None,
        req_max_lvl: int | None,
        is_hidden: bool,
        is_blue: bool,
        next_node_id: str | None,
        meta: dict[str, Any] | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO Choices (
                parent_node_id, text, req, req_lvl, req_max_lvl,
                is_hidden, is_blue, next_node_id, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parent_node_id,
                text,
                req,
                req_lvl,
                req_max_lvl,
                int(is_hidden),
                int(is_blue),
                next_node_id,
                json.dumps(meta, ensure_ascii=False) if meta else None,
            ),
        )
        self._choice_insert_count += 1

    def add_list_entry(self, list_node_id: str, child_node_id: str, weight: int = 1) -> None:
        self.conn.execute(
            """
            INSERT INTO List_Entries (list_node_id, child_node_id, weight)
            VALUES (?, ?, ?)
            """,
            (list_node_id, child_node_id, weight),
        )
        self._list_entry_count += 1

    def add_branch(
        self,
        parent_node_id: str,
        ship_name: str | None,
        branch_type: str,
        next_node_id: str,
        branch_payload: dict[str, Any] | None,
    ) -> None:
        normalized_type = branch_type
        if branch_type == "deadCrewAuto":
            normalized_type = "deadCrewAuto"

        self.conn.execute(
            """
            INSERT INTO Combat_Branches (
                parent_node_id, ship_name, branch_type, next_node_id, branch_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                parent_node_id,
                ship_name,
                normalized_type,
                next_node_id,
                json.dumps(branch_payload, ensure_ascii=False) if branch_payload else None,
            ),
        )
        self._branch_insert_count += 1

    def _choice_text(self, choice_elem: ET.Element) -> str | None:
        fragments: list[str] = []
        for child in choice_elem:
            if not isinstance(child.tag, str) or child.tag != "text":
                continue
            value = direct_text_value(child)
            if value:
                fragments.append(value)
        if fragments:
            return "\n".join(fragments)
        return None

    def _event_text(self, event_elem: ET.Element) -> str | None:
        fragments: list[str] = []
        for child in event_elem:
            if not isinstance(child.tag, str) or child.tag != "text":
                continue
            value = direct_text_value(child)
            if value:
                fragments.append(value)
        if fragments:
            return "\n".join(fragments)
        return None

    def _collect_effects(self, elem: ET.Element, skip_tags: set[str] | None = None) -> dict[str, Any]:
        skip_tags = skip_tags or set()
        payload: dict[str, Any] = {}

        for child in elem:
            if not isinstance(child.tag, str):
                continue
            if child.tag in skip_tags:
                continue
            append_payload(payload, child.tag, pack_element(child))

        return payload

    def _resolve_nested_event_target(self, elem: ET.Element, allow_reference: bool = True) -> str:
        if local_name(elem.tag) != "event":
            raise ValueError("Expected <event> element")

        event_name = elem.attrib.get("name")
        event_load = elem.attrib.get("load")
        if allow_reference and event_load and not event_name and not has_element_children(elem) and self._event_text(elem) is None:
            self.ensure_placeholder_node(event_load)
            return event_load

        node_id = event_name or event_load or f"anon_{uuid.uuid4().hex}"
        self.process_event(elem, explicit_id=node_id)
        return node_id

    def process_event(self, event_elem: ET.Element, explicit_id: str | None = None) -> str:
        if local_name(event_elem.tag) != "event":
            raise ValueError("Expected <event> element")

        node_id = explicit_id or event_elem.attrib.get("name") or event_elem.attrib.get("load") or f"anon_{uuid.uuid4().hex}"
        node_text = self._event_text(event_elem)
        is_unique = truthy(event_elem.attrib.get("unique"))

        self.upsert_node(
            node_id=node_id,
            node_type="EVENT",
            text=node_text,
            is_unique=is_unique,
            effects=None,
        )

        effects: dict[str, Any] = {}
        for child in event_elem:
            if not isinstance(child.tag, str):
                continue

            if child.tag == "text":
                continue

            if child.tag == "choice":
                self.process_choice(child, parent_node_id=node_id)
                continue

            if child.tag == "ship":
                ship_payload = self.process_ship(child, parent_node_id=node_id)
                append_payload(effects, "ship", ship_payload)
                continue

            if child.tag == "event":
                nested_target = self._resolve_nested_event_target(child, allow_reference=True)
                append_payload(effects, "event", {"next_node_id": nested_target})
                continue

            append_payload(effects, child.tag, pack_element(child))

        self.upsert_node(
            node_id=node_id,
            node_type="EVENT",
            text=node_text,
            is_unique=is_unique,
            effects=effects if effects else None,
        )
        return node_id

    def process_choice(self, choice_elem: ET.Element, parent_node_id: str) -> None:
        choice_text = self._choice_text(choice_elem)
        req = choice_elem.attrib.get("req")
        req_lvl = choice_elem.attrib.get("lvl") or choice_elem.attrib.get("min_level")
        req_max_lvl = choice_elem.attrib.get("max_lvl")
        is_hidden = truthy(choice_elem.attrib.get("hidden") or choice_elem.attrib.get("hiiden"))
        is_blue = truthy(choice_elem.attrib.get("blue"))

        meta: dict[str, Any] = {}
        next_node_id: str | None = None

        for child in choice_elem:
            if not isinstance(child.tag, str):
                continue

            if child.tag == "text":
                continue

            if child.tag == "event":
                next_node_id = self._resolve_nested_event_target(child, allow_reference=True)
                continue

            if child.tag == "ship":
                ship_payload = self.process_ship(child, parent_node_id=parent_node_id)
                append_payload(meta, "ship", ship_payload)
                continue

            append_payload(meta, child.tag, pack_element(child))

        self.add_choice(
            parent_node_id=parent_node_id,
            text=choice_text,
            req=req,
            req_lvl=int(req_lvl) if req_lvl is not None and str(req_lvl).isdigit() else None,
            req_max_lvl=int(req_max_lvl) if req_max_lvl is not None and str(req_max_lvl).isdigit() else None,
            is_hidden=is_hidden,
            is_blue=is_blue,
            next_node_id=next_node_id,
            meta=meta if meta else None,
        )

    def _branch_target_from_element(self, elem: ET.Element) -> str | None:
        if local_name(elem.tag) == "event":
            return self._resolve_nested_event_target(elem, allow_reference=True)

        if local_name(elem.tag) == "loadEvent":
            value = direct_text_value(elem)
            if value:
                self.ensure_placeholder_node(value)
                return value

        if local_name(elem.tag) == "choice":
            for child in elem:
                if not isinstance(child.tag, str):
                    continue
                target = self._branch_target_from_element(child)
                if target is not None:
                    return target
            return None

        for child in elem:
            if not isinstance(child.tag, str):
                continue
            target = self._branch_target_from_element(child)
            if target is not None:
                return target
        return None

    def process_ship(self, ship_elem: ET.Element, parent_node_id: str | None) -> dict[str, Any]:
        ship_payload: dict[str, Any] = {}
        ship_name = ship_elem.attrib.get("name") or ship_elem.attrib.get("load")
        for key, value in ship_elem.attrib.items():
            ship_payload[key] = value

        ship_node_id: str | None = None
        if parent_node_id is None:
            ship_node_id = ship_name or f"anon_{uuid.uuid4().hex}"
            self.upsert_node(
                node_id=ship_node_id,
                node_type="SHIP",
                text=ship_name,
                is_unique=truthy(ship_elem.attrib.get("unique")),
                effects=None,
            )

        for child in ship_elem:
            if not isinstance(child.tag, str):
                continue

            if child.tag in BRANCH_TYPES:
                branch_target = child.attrib.get("load")
                if branch_target is None:
                    branch_target = self._branch_target_from_element(child)

                branch_payload = pack_element(child)
                if branch_target is not None:
                    self.ensure_placeholder_node(branch_target)
                    if parent_node_id is not None:
                        self.add_branch(
                            parent_node_id=parent_node_id,
                            ship_name=ship_name,
                            branch_type=child.tag,
                            next_node_id=branch_target,
                            branch_payload=branch_payload,
                        )
                    else:
                        self.add_branch(
                            parent_node_id=ship_node_id,
                            ship_name=ship_name,
                            branch_type=child.tag,
                            next_node_id=branch_target,
                            branch_payload=branch_payload,
                        )
                else:
                    append_payload(ship_payload, child.tag, branch_payload)
                continue

            append_payload(ship_payload, child.tag, pack_element(child))

        if parent_node_id is None:
            self.upsert_node(
                node_id=ship_node_id,
                node_type="SHIP",
                text=ship_name,
                is_unique=truthy(ship_elem.attrib.get("unique")),
                effects=ship_payload if ship_payload else None,
            )
            return ship_payload

        return ship_payload

    def process_text_list(self, list_elem: ET.Element, list_node_id: str) -> None:
        index = 0
        for child in list_elem:
            if not isinstance(child.tag, str) or child.tag != "text":
                continue

            index += 1
            synthetic_id = f"{list_node_id}::text::{index}"
            text_value = child.attrib.get("id") or direct_text_value(child) or synthetic_id
            entry_payload = {key: value for key, value in child.attrib.items() if key != "id"}
            if child.text and child.text.strip():
                entry_payload["value"] = child.text.strip()

            self.upsert_node(
                node_id=synthetic_id,
                node_type="TEXT_ENTRY",
                text=text_value,
                is_unique=False,
                effects=entry_payload if entry_payload else None,
            )
            self.add_list_entry(list_node_id=list_node_id, child_node_id=synthetic_id)

    def process_event_list(self, list_elem: ET.Element, list_node_id: str) -> None:
        for child in list_elem:
            if not isinstance(child.tag, str) or child.tag != "event":
                continue

            child_node_id = self._resolve_nested_event_target(child, allow_reference=True)
            self.add_list_entry(list_node_id=list_node_id, child_node_id=child_node_id)

    def process_list_node(self, list_elem: ET.Element) -> str:
        list_tag = local_name(list_elem.tag)
        list_node_id = list_elem.attrib.get("name") or f"anon_{uuid.uuid4().hex}"
        is_unique = truthy(list_elem.attrib.get("unique"))
        list_payload = {key: value for key, value in list_elem.attrib.items() if key != "name"}

        if list_tag == "eventList":
            self.upsert_node(
                node_id=list_node_id,
                node_type="EVENT_LIST",
                text=None,
                is_unique=is_unique,
                effects=list_payload if list_payload else None,
            )
            self.process_event_list(list_elem, list_node_id)
        elif list_tag == "textList":
            self.upsert_node(
                node_id=list_node_id,
                node_type="TEXT_LIST",
                text=None,
                is_unique=is_unique,
                effects=list_payload if list_payload else None,
            )
            self.process_text_list(list_elem, list_node_id)
        else:
            raise ValueError(f"Unsupported list tag: {list_tag}")

        return list_node_id

    def process_top_level_element(self, elem: ET.Element) -> None:
        tag = local_name(elem.tag)

        if tag == "FTL":
            for child in elem:
                if not isinstance(child.tag, str):
                    continue
                self.process_top_level_element(child)
            return

        if tag == "event":
            self.process_event(elem)
            return

        if tag in {"eventList", "textList"}:
            self.process_list_node(elem)
            return

        if tag == "ship":
            self.process_ship(elem, parent_node_id=None)
            return

        self._ignored_root_count += 1

    def process_xml_file(self, file_path: str) -> None:
        self._file_count += 1
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()

            content = re.sub(r"<\?xml.*?\?>", "", content, flags=re.IGNORECASE | re.DOTALL)
            wrapped_content = f"<dummy_root>\n{content}\n</dummy_root>"
            root = ET.fromstring(wrapped_content)

            for child in root:
                if not isinstance(child.tag, str):
                    continue
                self.process_top_level_element(child)

            self.conn.commit()
        except ET.ParseError as exc:
            self.conn.rollback()
            self._parse_error_count += 1
            print(f"[-] XML parse error {os.path.basename(file_path)}: {exc}")
        except Exception as exc:
            self.conn.rollback()
            self._parse_error_count += 1
            print(f"[-] Other error {os.path.basename(file_path)}: {exc}")

    def process_path(self, input_path: str) -> None:
        path = Path(input_path)
        if path.is_file():
            self.process_xml_file(str(path))
            return

        xml_files = sorted(path.rglob("*.xml"))
        for xml_file in xml_files:
            self.process_xml_file(str(xml_file))

    def print_summary(self) -> None:
        node_count = self.conn.execute("SELECT COUNT(*) FROM Nodes").fetchone()[0]
        choice_count = self.conn.execute("SELECT COUNT(*) FROM Choices").fetchone()[0]
        list_count = self.conn.execute("SELECT COUNT(*) FROM List_Entries").fetchone()[0]
        branch_count = self.conn.execute("SELECT COUNT(*) FROM Combat_Branches").fetchone()[0]

        print("=== FTL XML -> SQLite preprocessing complete ===")
        print(f"Scanned XML files: {self._file_count}")
        print(f"Parse failures: {self._parse_error_count}")
        print(f"Ignored root-level non-story nodes: {self._ignored_root_count}")
        print(f"Nodes rows: {node_count}")
        print(f"Choices rows: {choice_count}")
        print(f"List_Entries rows: {list_count}")
        print(f"Combat_Branches rows: {branch_count}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preprocess FTL XML files into SQLite tables.")
    parser.add_argument(
        "input_path",
        nargs="?",
        default=str(Path(__file__).resolve().parent / "gamedata"),
        help="XML file or directory to process.",
    )
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent / "ftl_events.sqlite"),
        help="Output SQLite database path.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    builder = FTLSQLitePreprocessor(args.db)
    try:
        builder.process_path(args.input_path)
        builder.print_summary()
    finally:
        builder.close()


if __name__ == "__main__":
    main()