"""Repository layer. Protocol interfaces + a SQLite JSON document store (stdlib only).

PostGIS/Supabase remains the target store (DATA_ARCHITECTURE §6.9, design DDL in backend/db/schema.sql);
swapping it in means implementing `DocumentStore` (or the typed repositories) against Postgres.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class DocumentStore(Protocol):
    def get(self, collection: str, doc_id: str) -> dict | None: ...
    def put(self, collection: str, doc_id: str, body: dict, parent: str | None = None) -> None: ...
    def delete(self, collection: str, doc_id: str) -> bool: ...
    def list(self, collection: str, parent: str | None = None) -> list[dict]: ...
    def delete_children(self, parent: str) -> int: ...


class SqliteDocumentStore:
    """Thread-safe single-connection SQLite store. `path=":memory:"` for tests."""

    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL") if path != ":memory:" else None
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS docs (collection TEXT NOT NULL, id TEXT NOT NULL, parent TEXT, "
                "body TEXT NOT NULL, seq INTEGER NOT NULL, PRIMARY KEY (collection, id))"
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS docs_parent ON docs (collection, parent)")
            self._seq = self._conn.execute("SELECT COALESCE(MAX(seq), 0) FROM docs").fetchone()[0]

    def get(self, collection: str, doc_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT body FROM docs WHERE collection=? AND id=?", (collection, doc_id)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, collection: str, doc_id: str, body: dict, parent: str | None = None) -> None:
        with self._lock:
            existing = self._conn.execute(
                "SELECT seq FROM docs WHERE collection=? AND id=?", (collection, doc_id)
            ).fetchone()
            if existing:
                seq = existing[0]
            else:
                self._seq += 1
                seq = self._seq
            self._conn.execute(
                "INSERT OR REPLACE INTO docs (collection, id, parent, body, seq) VALUES (?, ?, ?, ?, ?)",
                (collection, doc_id, parent, json.dumps(body), seq),
            )

    def delete(self, collection: str, doc_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM docs WHERE collection=? AND id=?", (collection, doc_id))
        return cur.rowcount > 0

    def list(self, collection: str, parent: str | None = None) -> list[dict]:
        with self._lock:
            if parent is None:
                rows = self._conn.execute("SELECT body FROM docs WHERE collection=? ORDER BY seq", (collection,))
            else:
                rows = self._conn.execute(
                    "SELECT body FROM docs WHERE collection=? AND parent=? ORDER BY seq", (collection, parent)
                )
            return [json.loads(r[0]) for r in rows.fetchall()]

    def delete_children(self, parent: str) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM docs WHERE parent=?", (parent,))
        return cur.rowcount


class ModelRepository(Generic[M]):
    """Typed repository over one collection of a DocumentStore."""

    def __init__(self, store: DocumentStore, collection: str, model: type[M]):
        self._store = store
        self.collection = collection
        self.model = model

    def get(self, doc_id: str) -> M | None:
        body = self._store.get(self.collection, str(doc_id))
        return self.model.model_validate(body) if body is not None else None

    def put(self, doc_id: str, item: M, parent: str | None = None) -> M:
        self._store.put(self.collection, str(doc_id), item.model_dump(mode="json"), parent=str(parent) if parent else None)
        return item

    def delete(self, doc_id: str) -> bool:
        return self._store.delete(self.collection, str(doc_id))

    def list(self, parent: str | None = None) -> list[M]:
        return [self.model.model_validate(b) for b in self._store.list(self.collection, str(parent) if parent else None)]

    def put_many(self, items: Iterable[tuple[str, M, str | None]]) -> None:
        for doc_id, item, parent in items:
            self.put(doc_id, item, parent)
