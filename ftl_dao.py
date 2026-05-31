from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple, Optional


class FTLDAO:
    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = self._resolve_default_db_path()

        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row

    @staticmethod
    def _candidate_db_paths() -> List[Path]:
        candidates = [Path("ftl_output.sqlite"), Path("ftl_output.db")]

        if getattr(sys, "frozen", False):
            executable_dir = Path(sys.executable).resolve().parent
            candidates.extend(
                [
                    executable_dir / "ftl_output.sqlite",
                    executable_dir / "ftl_output.db",
                ]
            )

            bundle_dir = Path(getattr(sys, "_MEIPASS", executable_dir))
            candidates.extend(
                [
                    bundle_dir / "ftl_output.sqlite",
                    bundle_dir / "ftl_output.db",
                ]
            )

        return candidates

    @classmethod
    def _resolve_default_db_path(cls) -> str:
        for candidate in cls._candidate_db_paths():
            if candidate.exists():
                return str(candidate)

        return str(Path("ftl_output.sqlite"))

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def has_nodes(self) -> bool:
        cur = self._conn.cursor()
        cur.execute("SELECT 1 FROM Nodes LIMIT 1")
        return cur.fetchone() is not None

    def search_nodes(self, keyword: str, limit: int = 500) -> List[Tuple[str, str]]:
        """Fuzzy search Nodes by id or text. Returns list of (id, text).

        Uses simple LIKE with wildcards. Caller is responsible for UI-rate limiting.
        """
        if not keyword:
            return []
        # prepare pattern for LIKE
        pat = f"%{keyword}%"
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, text FROM Nodes WHERE id LIKE ? OR text LIKE ? ORDER BY id LIMIT ?",
            (pat, pat, limit),
        )
        rows = cur.fetchall()
        return [(r["id"], r["text"] or "") for r in rows]

    def get_node(self, node_id: str) -> Optional[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM Nodes WHERE id = ?", (node_id,))
        row = cur.fetchone()
        return row

    def get_choices(self, parent_node_id: str) -> List[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, parent_node_id, text, req, is_hidden, is_blue, next_node_id FROM Choices WHERE parent_node_id = ? ORDER BY id",
            (parent_node_id,),
        )
        return cur.fetchall()

    def get_list_entries(self, list_node_id: str) -> List[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, list_node_id, child_node_id FROM List_Entries WHERE list_node_id = ? ORDER BY id",
            (list_node_id,),
        )
        return cur.fetchall()

    def get_branches(self, parent_node_id: str) -> List[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, parent_node_id, ship_name, branch_type, next_node_id, branch_json FROM Combat_Branches WHERE parent_node_id = ? ORDER BY id",
            (parent_node_id,),
        )
        return cur.fetchall()

    def get_parent_links(self, node_id: str) -> List[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT parent_id, relation_type
            FROM (
                SELECT parent_node_id AS parent_id, 'CHOICE' AS relation_type, 1 AS relation_order
                FROM Choices
                WHERE next_node_id = ?

                UNION ALL

                SELECT parent_node_id AS parent_id, 'BRANCH' AS relation_type, 2 AS relation_order
                FROM Combat_Branches
                WHERE next_node_id = ?

                UNION ALL

                SELECT list_node_id AS parent_id, 'LIST_ENTRY' AS relation_type, 3 AS relation_order
                FROM List_Entries
                WHERE child_node_id = ?
            )
            WHERE parent_id IS NOT NULL
            ORDER BY relation_order, parent_id
            """,
            (node_id, node_id, node_id),
        )
        return cur.fetchall()


if __name__ == "__main__":
    # quick sanity check
    dao = FTLDAO()
    print("Connected to:", dao._db_path)
    print("Sample search:", dao.search_nodes("BOSS", limit=10))
    dao.close()
