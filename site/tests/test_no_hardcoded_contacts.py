"""BRIEF.md раздел 19.2: рекурсивный grep по templates/, static/, api/app/ на паттерны
+996, @example, wa.me/, example.kg. Найдено вне config.json -> тест падает.

Уточнение по wa.me/: сам домен обязан встречаться в шаблонах и JS (это структурная
часть ссылки на WhatsApp-чат, собираемой из config.whatsapp на лету), поэтому здесь
ищется не сам домен, а признак ЗАХАРДКОЖЕННОГО номера сразу после него (wa.me/996...) —
именно это раздел 19.1 запрещает. См. DECISIONS.md."""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [REPO_ROOT / "site" / "templates", REPO_ROOT / "site" / "static", REPO_ROOT / "api" / "app"]
TEXT_EXTENSIONS = {".html", ".css", ".js", ".svg", ".py"}

PATTERNS = {
    "демо-телефон +996": re.compile(r"\+996"),
    "демо-email @example": re.compile(r"@example"),
    "демо-домен example.kg": re.compile(r"example\.kg"),
    "захардкоженный номер в wa.me-ссылке": re.compile(r"wa\.me/\d"),
}

# api/app/utils.py: докстрока normalize_kg_phone() ИЛЛЮСТРИРУЕТ принимаемые форматы номера
# ('+996 555 12-34-56' и т.п.) — это документация формата, а не захардкоженное контактное
# значение компании, подставляемое куда-либо вместо чтения из config.json.
ALLOWLIST = {REPO_ROOT / "api" / "app" / "utils.py"}


def _iter_files():
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in TEXT_EXTENSIONS and path not in ALLOWLIST:
                yield path


def test_no_hardcoded_contacts_outside_config():
    violations = []
    for path in _iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {label} -> {match.group(0)!r}")
    assert not violations, "Найдены захардкоженные контакты вне config.json:\n" + "\n".join(violations)
