from __future__ import annotations

import configparser
import json
import mimetypes
import os
import shutil
import sqlite3
import subprocess
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from .models import IndexStats, SearchIntent, SearchResult, user_data_dir
from .nlp import date_bounds


TEXT_EXTENSIONS = {
    ".c",
    ".conf",
    ".cpp",
    ".css",
    ".csv",
    ".dart",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".log",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".cache",
    ".config",
    ".git",
    ".local",
    ".npm",
    ".pub-cache",
    ".rustup",
    ".var",
    "node_modules",
    "build",
}

TYPE_EXTENSIONS = {
    "package": {".appimage", ".deb", ".flatpak", ".flatpakref", ".rpm"},
    "pdf": {".pdf"},
    "image": {".avif", ".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".svg", ".webp"},
    "video": {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"},
    "audio": {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"},
    "text": TEXT_EXTENSIONS,
    "document": {".doc", ".docx", ".odt", ".rtf"},
    "spreadsheet": {".csv", ".ods", ".xls", ".xlsx"},
    "presentation": {".odp", ".ppt", ".pptx"},
    "code": TEXT_EXTENSIONS - {".txt", ".md", ".csv", ".log"},
}


def default_roots() -> list[Path]:
    return [Path.home()]


class SearchIndex:
    def __init__(self, database: Path | None = None) -> None:
        data_dir = user_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.database = database or data_dir / "index.db"
        self.connection = sqlite3.connect(self.database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                extension TEXT NOT NULL,
                mime TEXT,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                ctime REAL NOT NULL DEFAULT 0,
                content TEXT NOT NULL DEFAULT ''
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                path UNINDEXED, name, content, tokenize='unicode61'
            );
            CREATE TABLE IF NOT EXISTS applications (
                desktop_file TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                executable TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT 'application-x-executable'
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS applications_fts USING fts5(
                desktop_file UNINDEXED, name, description, tokenize='unicode61'
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(files)")
        }
        if "ctime" not in columns:
            self.connection.execute(
                "ALTER TABLE files ADD COLUMN ctime REAL NOT NULL DEFAULT 0"
            )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _walk(self, roots: Iterable[Path]) -> Iterable[Path]:
        database_path = str(self.database.resolve())
        for root in roots:
            if not root.exists():
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [
                    directory
                    for directory in dirs
                    if directory not in SKIP_DIRS and not directory.startswith(".")
                ]
                for filename in files:
                    if filename.startswith("."):
                        continue
                    candidate = Path(current) / filename
                    candidate_path = str(candidate.resolve())
                    if candidate_path == database_path or candidate_path.startswith(
                        database_path + "-"
                    ):
                        continue
                    yield candidate

    def _read_content(self, path: Path, size: int) -> str:
        if size > 2_000_000:
            return ""
        suffix = path.suffix.lower()
        try:
            if suffix in TEXT_EXTENSIONS:
                return path.read_text(encoding="utf-8", errors="ignore")[:100_000]
            if suffix == ".pdf" and shutil.which("pdftotext"):
                completed = subprocess.run(
                    ["pdftotext", "-f", "1", "-l", "20", str(path), "-"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=12,
                )
                if completed.returncode == 0:
                    return completed.stdout[:100_000]
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def rebuild(
        self,
        roots: list[Path] | None = None,
        progress: Callable[[str], None] | None = None,
        max_files: int = 30_000,
    ) -> IndexStats:
        selected_roots = roots or default_roots()
        stats = IndexStats()
        self.connection.execute("DELETE FROM files")
        self.connection.execute("DELETE FROM files_fts")
        self.connection.execute("DELETE FROM applications")
        self.connection.execute("DELETE FROM applications_fts")

        for path in self._walk(selected_roots):
            if stats.files >= max_files:
                break
            try:
                file_stat = path.stat()
                if not path.is_file():
                    continue
                content = self._read_content(path, file_stat.st_size)
                mime = mimetypes.guess_type(path.name)[0] or ""
                row = (
                    str(path),
                    path.name,
                    path.suffix.lower(),
                    mime,
                    file_stat.st_size,
                    file_stat.st_mtime,
                    file_stat.st_ctime,
                    content,
                )
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO files(
                        path, name, extension, mime, size, mtime, ctime, content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
                self.connection.execute(
                    "INSERT INTO files_fts(path, name, content) VALUES (?, ?, ?)",
                    (str(path), path.name, content),
                )
                stats.files += 1
                if progress and stats.files % 100 == 0:
                    progress(f"{stats.files} dosya indekslendi…")
            except (OSError, sqlite3.Error):
                stats.skipped += 1

        stats.applications = self._index_applications()
        stats.indexed_at = datetime.now().isoformat(timespec="seconds")
        self.connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('stats', ?)",
            (json.dumps(stats.__dict__ if hasattr(stats, "__dict__") else {
                "files": stats.files,
                "applications": stats.applications,
                "skipped": stats.skipped,
                "indexed_at": stats.indexed_at,
            }),),
        )
        self.connection.commit()
        return stats

    def _index_applications(self) -> int:
        directories = [
            Path("/usr/share/applications"),
            Path.home() / ".local/share/applications",
        ]
        count = 0
        for directory in directories:
            if not directory.exists():
                continue
            for desktop_file in directory.glob("*.desktop"):
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                try:
                    parser.read(desktop_file, encoding="utf-8")
                    entry = parser["Desktop Entry"]
                    if entry.get("NoDisplay", "false").lower() == "true":
                        continue
                    name = entry.get("Name", "").strip()
                    executable = entry.get("Exec", "").strip()
                    if not name or not executable:
                        continue
                    description = entry.get("Comment", "").strip()
                    icon = entry.get("Icon", "application-x-executable").strip()
                    row = (str(desktop_file), name, description, executable, icon)
                    self.connection.execute(
                        "INSERT OR REPLACE INTO applications VALUES (?, ?, ?, ?, ?)", row
                    )
                    self.connection.execute(
                        "INSERT INTO applications_fts VALUES (?, ?, ?)",
                        (str(desktop_file), name, description),
                    )
                    count += 1
                except (configparser.Error, KeyError, OSError):
                    continue
        return count

    def stats(self) -> IndexStats:
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key='stats'"
        ).fetchone()
        if not row:
            return IndexStats()
        try:
            return IndexStats(**json.loads(row["value"]))
        except (TypeError, ValueError):
            return IndexStats()

    @staticmethod
    def _fts_expression(keywords: list[str]) -> str:
        cleaned = []
        for keyword in keywords:
            token = "".join(char for char in keyword if char.isalnum() or char in "_-")
            if token:
                cleaned.append(f'"{token}"*')
        return " OR ".join(cleaned)

    def search(self, intent: SearchIntent, limit: int = 20) -> list[SearchResult]:
        results: list[SearchResult] = []
        expression = self._fts_expression(intent.keywords)
        start, end = date_bounds(intent.date_filter, intent.date_from, intent.date_to)
        extensions = TYPE_EXTENSIONS.get(intent.file_type or "")

        file_sql = """
                SELECT f.path, f.name, f.extension, f.mime, f.size, f.mtime, f.ctime,
                   snippet(files_fts, 2, '', '', ' … ', 18) AS snippet,
                   bm25(files_fts, 1.2, 2.2) AS rank
            FROM files_fts
            JOIN files f ON f.path = files_fts.path
        """
        conditions: list[str] = []
        parameters: list[object] = []
        if expression:
            conditions.append("files_fts MATCH ?")
            parameters.append(expression)
        if intent.file_type == "package" and extensions:
            placeholders = ",".join("?" for _ in extensions)
            conditions.append(
                f"(f.extension IN ({placeholders}) "
                "OR (f.extension = '.sh' AND "
                "(lower(f.name) LIKE '%install%' "
                "OR lower(f.name) LIKE '%kurulum%' "
                "OR lower(f.name) LIKE '%setup%')))"
            )
            parameters.extend(sorted(extensions))
        elif extensions:
            placeholders = ",".join("?" for _ in extensions)
            conditions.append(f"f.extension IN ({placeholders})")
            parameters.extend(sorted(extensions))
        if start is not None and end is not None:
            conditions.append(
                "((f.mtime >= ? AND f.mtime < ?) "
                "OR (f.ctime >= ? AND f.ctime < ?))"
            )
            parameters.extend((start, end, start, end))
        elif start is not None:
            conditions.append("(f.mtime >= ? OR f.ctime >= ?)")
            parameters.extend((start, start))
        elif end is not None:
            conditions.append("(f.mtime < ? OR f.ctime < ?)")
            parameters.extend((end, end))
        if conditions:
            file_sql += " WHERE " + " AND ".join(conditions)
        file_sql += " ORDER BY rank, f.mtime DESC LIMIT ?"
        parameters.append(limit)

        try:
            for row in self.connection.execute(file_sql, parameters):
                modified = datetime.fromtimestamp(row["mtime"]).strftime("%d.%m.%Y %H:%M")
                size = self._format_size(row["size"])
                results.append(
                    SearchResult(
                        result_type="file",
                        title=row["name"],
                        subtitle=f"{row['path']}  •  {size}  •  {modified}",
                        target=row["path"],
                        score=float(-row["rank"]),
                        snippet=(row["snippet"] or "").replace("\n", " ").strip(),
                        icon=self._icon_for(row["extension"], row["mime"]),
                    )
                )
        except sqlite3.OperationalError:
            pass

        if not intent.file_type and not intent.date_filter and expression:
            app_sql = """
                SELECT a.desktop_file, a.name, a.description, a.icon,
                       bm25(applications_fts) AS rank
                FROM applications_fts
                JOIN applications a
                  ON a.desktop_file = applications_fts.desktop_file
                WHERE applications_fts MATCH ?
                ORDER BY rank LIMIT ?
            """
            try:
                for row in self.connection.execute(app_sql, (expression, limit)):
                    results.append(
                        SearchResult(
                            result_type="application",
                            title=row["name"],
                            subtitle=row["description"] or "Uygulamayı aç",
                            target=row["desktop_file"],
                            score=float(-row["rank"]) + 2,
                            icon=row["icon"] or "application-x-executable",
                        )
                    )
            except sqlite3.OperationalError:
                pass

        results.sort(key=lambda item: item.score, reverse=True)
        if not results and intent.file_type and intent.keywords:
            return self.search(replace(intent, keywords=[]), limit=limit)
        return results[:limit]

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} GB"

    @staticmethod
    def _icon_for(extension: str, mime: str) -> str:
        if extension == ".pdf":
            return "application-pdf-symbolic"
        if extension in TYPE_EXTENSIONS["package"]:
            return "package-x-generic-symbolic"
        if mime.startswith("image/"):
            return "image-x-generic-symbolic"
        if mime.startswith("video/"):
            return "video-x-generic-symbolic"
        if mime.startswith("audio/"):
            return "audio-x-generic-symbolic"
        if extension in TEXT_EXTENSIONS:
            return "text-x-generic-symbolic"
        return "document-open-symbolic"
