#!/usr/bin/env python3
"""
Leak & Secret Scanner for the GHG Platform Sandbox Package
==========================================================
Scans source files, SQLite database bytes (including unallocated/freelist pages),
frontend dist bundles, PDFs (extracted text, compressed streams, and non-binary text),
and log files for real client identifiers or retired credentials.

Zero hits are required in the release sandbox package.
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sqlite3
import sys
import zlib
from collections.abc import Iterable
from pathlib import Path

# Base64-encoded forbidden client/secret tokens so this scanner never self-triggers.
_ENCODED_TOKENS: list[tuple[str, bytes, str]] = [
    ("token_01", b"U29uYXRyYWNo", "substr"),
    ("token_02", b"QmVya2luZQ==", "substr"),
    ("token_03", b"T2NjaWRlbnRhbA==", "substr"),
    ("token_04", b"T3h5", "short_word"),
    ("token_05", b"RW5p", "short_word"),
    ("token_06", b"SEJOUw==", "substr"),
    ("token_07", b"RWwgTWVyaw==", "space_flex"),
    ("token_08", b"SGFzc2k=", "prefix_word"),
    ("token_09", b"UmhvdXJkZQ==", "substr"),
    ("token_10", b"QmVsaGFkag==", "substr"),
    ("token_11", b"TWFuc291cmk=", "substr"),
    ("token_12", b"S2hlbGlmaQ==", "substr"),
    ("token_13", b"c29uYXRyYWNoLmR6", "substr"),
    ("token_14", b"Q0RTRV9WYXVsdA==", "substr"),
    ("token_15", b"R3JvdXBlbWVudA==", "substr"),
]

SQLITE_EXTS = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm"}
BINARY_SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".wav", ".zip", ".gz", ".whl", ".pyc",
}
DEFAULT_EXCLUDED_DIRS = {
    ".git", ".agents", "node_modules", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".hypothesis", ".tmp", "private_fixtures", "backups",
    "audit", "screenshots", "test-results", "playwright-report",
}


def _build_patterns() -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for _label, b64, mode in _ENCODED_TOKENS:
        term = base64.b64decode(b64).decode("utf-8")
        if mode == "substr":
            pat = re.compile(re.escape(term), re.IGNORECASE)
        elif mode == "space_flex":
            pat = re.compile(re.escape(term).replace(r"\ ", r"[\s_\-]*"), re.IGNORECASE)
        elif mode == "prefix_word":
            pat = re.compile(r"(?<![A-Za-z])" + re.escape(term), re.IGNORECASE)
        elif mode == "short_word":
            pat = re.compile(
                r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"
                r"|(?<![a-z])" + re.escape(term) + r"(?=[A-Z0-9_\W]|$)"
            )
        else:
            pat = re.compile(re.escape(term), re.IGNORECASE)
        patterns.append((term, pat))
    return patterns


_PATTERNS = _build_patterns()


def scan_text(text: str, source_label: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    if not text:
        return hits
    for term, pat in _PATTERNS:
        m = pat.search(text)
        if m:
            prefix = text[: m.start()]
            line_no = prefix.count("\n") + 1
            snippet = text[max(0, m.start() - 30) : min(len(text), m.end() + 30)].replace("\n", " ").replace("\r", " ")
            hits.append({
                "file": source_label,
                "term": term,
                "location": f"line {line_no}",
                "snippet": snippet,
            })
    return hits


def scan_sqlite_file(path: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    raw = path.read_bytes()

    # 1. Scan raw database file bytes across all pages (captures unallocated space and freelist pages)
    decoded_utf8 = raw.decode("utf-8", errors="ignore")
    for term, pat in _PATTERNS:
        for m in pat.finditer(decoded_utf8):
            snippet = decoded_utf8[max(0, m.start() - 25) : min(len(decoded_utf8), m.end() + 25)]
            snippet_clean = "".join(ch if 32 <= ord(ch) < 127 else "." for ch in snippet)
            hits.append({
                "file": str(path),
                "term": term,
                "location": f"raw-bytes offset {m.start()}",
                "snippet": snippet_clean,
            })
            break

    # 2. Check UTF-16LE encoding inside SQLite (in case DB encoding uses UTF-16)
    decoded_u16 = raw.decode("utf-16-le", errors="ignore")
    for term, pat in _PATTERNS:
        m = pat.search(decoded_u16)
        if m:
            hits.append({
                "file": str(path),
                "term": term,
                "location": f"utf16-bytes offset {m.start()}",
                "snippet": m.group(0),
            })

    # 3. Query all SQLite tables if valid main DB file
    if path.suffix.lower() in (".db", ".sqlite", ".sqlite3") and raw.startswith(b"SQLite format 3\x00"):
        try:
            uri = f"file:{path.as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            cur = conn.cursor()
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for tbl in tables:
                safe_tbl = tbl.replace('"', '""')
                for row in cur.execute(f'SELECT * FROM "{safe_tbl}"').fetchall():
                    row_str = " ".join(str(v) for v in row if v is not None)
                    for term, pat in _PATTERNS:
                        if pat.search(row_str):
                            hits.append({
                                "file": str(path),
                                "term": term,
                                "location": f"table {tbl}",
                                "snippet": row_str[:80],
                            })
                            break
            freelist_count = cur.execute("PRAGMA freelist_count").fetchone()
            if freelist_count and freelist_count[0] > 0:
                hits.append({
                    "file": str(path),
                    "term": "FREELIST_NOT_VACUUMED",
                    "location": f"freelist_count={freelist_count[0]}",
                    "snippet": "Database has unvacuumed freelist pages",
                })
            conn.close()
        except Exception:
            pass

    return hits


def scan_pdf_file(path: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    raw = path.read_bytes()

    # 1. Scan non-binary PDF sections (metadata/objects outside compressed stream payloads)
    stripped = re.sub(rb"stream\r?\n.*?\r?\nendstream", b" ", raw, flags=re.DOTALL)
    header_txt = stripped.decode("latin-1", errors="ignore")
    for h in scan_text(header_txt, str(path)):
        h["location"] = f"pdf-metadata {h['location']}"
        hits.append(h)

    # 2. Decompress FlateDecode / zlib streams inside PDF
    for idx, m in enumerate(re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.DOTALL)):
        stream_data = m.group(1)
        try:
            decomp = zlib.decompress(stream_data).decode("latin-1", errors="ignore")
            for h in scan_text(decomp, str(path)):
                h["location"] = f"pdf-stream-{idx}"
                hits.append(h)
        except Exception:
            pass

    # 3. Extract visible page text via pypdfium2 (fast) or pdfplumber
    extracted = False
    try:
        import pypdfium2  # type: ignore

        pdf = pypdfium2.PdfDocument(str(path))
        try:
            for p_idx in range(len(pdf)):
                txt = pdf[p_idx].get_textpage().get_text_range() or ""
                for h in scan_text(txt, str(path)):
                    h["location"] = f"pdf-page-{p_idx + 1}"
                    hits.append(h)
        finally:
            pdf.close()
        extracted = True
    except Exception:
        pass

    if not extracted:
        try:
            import pdfplumber  # type: ignore

            with pdfplumber.open(str(path)) as pdf:
                for p_idx, page in enumerate(pdf.pages, 1):
                    txt = page.extract_text() or ""
                    for h in scan_text(txt, str(path)):
                        h["location"] = f"pdf-page-{p_idx}"
                        hits.append(h)
        except Exception:
            pass

    return hits


def iter_files(roots: Iterable[Path], sandbox_mode: bool = False) -> Iterable[Path]:
    for root in roots:
        if root.is_file():
            yield root
            continue
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if not sandbox_mode:
                dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDED_DIRS]
            else:
                dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "__pycache__", ".pytest_cache"}]
            for fname in filenames:
                yield Path(dirpath) / fname


def scan_paths(paths: list[Path], sandbox_mode: bool = False) -> list[dict[str, str]]:
    all_hits: list[dict[str, str]] = []
    for fpath in iter_files(paths, sandbox_mode=sandbox_mode):
        fname_hits = scan_text(fpath.as_posix(), str(fpath))
        for fh in fname_hits:
            fh["location"] = "filename"
            all_hits.append(fh)

        suffix = fpath.suffix.lower()
        if suffix in BINARY_SKIP_EXTS:
            continue
        try:
            if suffix in SQLITE_EXTS:
                all_hits.extend(scan_sqlite_file(fpath))
            elif suffix == ".pdf":
                all_hits.extend(scan_pdf_file(fpath))
            else:
                raw = fpath.read_bytes()
                try:
                    txt = raw.decode("utf-8")
                except UnicodeDecodeError:
                    txt = raw.decode("latin-1", errors="ignore")
                all_hits.extend(scan_text(txt, str(fpath)))
        except OSError as exc:
            all_hits.append({
                "file": str(fpath),
                "term": "READ_ERROR",
                "location": "io",
                "snippet": str(exc),
            })
    return all_hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan repository or sandbox package for client data or secrets.")
    parser.add_argument("paths", nargs="*", help="Paths to scan (default: repo root).")
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="Strict sandbox mode: scans every non-node_modules/.git file without dev exclusions.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    targets = [Path(p).resolve() for p in args.paths] if args.paths else [repo_root]

    hits = scan_paths(targets, sandbox_mode=args.sandbox)
    if hits:
        print(f"[FAIL] Leak scan detected {len(hits)} hit(s):")
        for h in hits:
            print(f"  - {h['file']} ({h['location']}) matched '{h['term']}': {h['snippet'][:90]}")
        return 1

    print(f"[PASS] Leak scan clean: 0 hits across {len(targets)} target path(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
