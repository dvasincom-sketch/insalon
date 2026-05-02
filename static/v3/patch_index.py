#!/usr/bin/env python3
"""
patch_index.py — точный патч index.html для Dev Log
Запуск из корня проекта: python3 patch_index.py
"""

from pathlib import Path
import sys

INDEX = Path("static/v3/index.html")

if not INDEX.exists():
    sys.exit(f"❌ Файл не найден: {INDEX}")

html = INDEX.read_text(encoding="utf-8")
changed = False

# ── 1. Nav item — вставить после блока li "Обязательства" ────────────────────
NAV_ANCHOR = '            <a class="nav-link" href="#obligations" data-screen="obligations">'
NAV_ITEM = '''
          <li class="nav-item">
            <a class="nav-link" href="#devlog" data-screen="devlog">
              <span class="nav-link-icon d-md-none d-lg-inline-block">
                <i class="ti ti-code"></i>
              </span>
              <span class="nav-link-title">Dev Log</span>
            </a>
          </li>'''

if 'data-screen="devlog"' in html:
    print("⏭  Nav item уже есть")
elif NAV_ANCHOR not in html:
    sys.exit("❌ Не нашёл якорь nav (блок obligations)")
else:
    start = html.index(NAV_ANCHOR)
    li_end = html.index("</li>", start) + len("</li>")
    html = html[:li_end] + NAV_ITEM + html[li_end:]
    print("✅ Nav item добавлен после Обязательства")
    changed = True

# ── 2. Screen div — вставить перед закрывающим </div></div> page-wrapper ──────
SCREEN_ANCHOR = "    </div>\n\n  </div>\n</div>\n\n<!-- Detail Modal -->"
SCREEN_DIV    = "    </div>\n\n    <!-- Screen: Dev Log -->\n    <div class=\"page-body d-none\" id=\"screen-devlog\"></div>\n\n  </div>\n</div>\n\n<!-- Detail Modal -->"

if 'id="screen-devlog"' in html:
    print("⏭  Screen div уже есть")
elif SCREEN_ANCHOR not in html:
    sys.exit("❌ Не нашёл якорь для screen-devlog")
else:
    html = html.replace(SCREEN_ANCHOR, SCREEN_DIV, 1)
    print("✅ Screen div добавлен")
    changed = True

# ── 3. Script tag — вставить после obligations.js ─────────────────────────────
SCRIPT_ANCHOR = '<script src="js/obligations.js"></script>'
SCRIPT_NEW    = '<script src="js/obligations.js"></script>\n<script src="js/devlog.js"></script>'

if "devlog.js" in html:
    print("⏭  Script tag уже есть")
elif SCRIPT_ANCHOR not in html:
    sys.exit("❌ Не нашёл js/obligations.js")
else:
    html = html.replace(SCRIPT_ANCHOR, SCRIPT_NEW, 1)
    print("✅ Script tag добавлен")
    changed = True

# ── Сохранить ──────────────────────────────────────────────────────────────────
if changed:
    INDEX.write_text(html, encoding="utf-8")
    print(f"\n✅ {INDEX} сохранён")
else:
    print("\nℹ️  Всё уже применено, файл не изменён")
