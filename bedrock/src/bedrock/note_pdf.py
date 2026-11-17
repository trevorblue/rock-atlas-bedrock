"""Render the research note (reports/bedrock_note.md) to a print-ready PDF.

    python -m bedrock.note_pdf                                  # -> reports/bedrock_note.pdf
    python -m bedrock.note_pdf --repo github.com/you/bedrock    # fills in the repo link

Needs `playwright` and a Chrome/Edge install (optional tool, not used by the pipeline or the app).
Run `python -m bedrock.figures` first so the charts are current.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import markdown

from .config import ROOT

REPORTS = ROOT / "reports"
SRC, OUT = REPORTS / "bedrock_note.md", REPORTS / "bedrock_note.pdf"
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "/usr/bin/google-chrome", "/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]

CSS = """
@page { size: A4; margin: 12mm 14mm 13mm 14mm; }
:root { --ink:#1f1f1f; --muted:#5f5f5a; --rule:#dcdcd7; --accent:#b8322f; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 9pt; line-height: 1.34;
       color: var(--ink); background: #fff; margin: 0; }
h1 { font-size: 19pt; line-height: 1.15; margin: 0 0 3pt; letter-spacing: -0.2pt; }
h1 + p { color: var(--muted); font-size: 8.6pt; margin: 0 0 8pt; padding-bottom: 6pt; border-bottom: 2px solid var(--ink); }
h2 { font-size: 11.4pt; margin: 9pt 0 3pt; break-after: avoid; }
p { margin: 0 0 5pt; } ul { margin: 0 0 5pt; padding-left: 15pt; } li { margin: 0 0 2.5pt; }
strong { font-weight: 650; }
code { font-family: Consolas, monospace; font-size: 8.4pt; background: #f2f2ef; padding: 0 2pt; border-radius: 2px; }
img { display: block; width: 66%; margin: 2pt auto 5pt; break-inside: avoid; }
p:has(> img) { break-inside: avoid; margin: 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 6pt; break-inside: avoid; }
td { border-top: 1px solid var(--rule); padding: 3.5pt 6pt; vertical-align: middle; }
tr:last-child td { border-bottom: 1px solid var(--rule); }
td:first-child { font-size: 13.5pt; font-weight: 700; white-space: nowrap; width: 1%; color: var(--accent); }
"""


def build_html(md_text: str, repo: str | None) -> str:
    if repo:
        md_text = md_text.replace("github.com/&lt;your-account&gt;/bedrock", repo)
    body = markdown.markdown(md_text, extensions=["tables"])
    body = re.sub(r"<thead>\s*<tr>(\s*<th[^>]*>\s*</th>)+\s*</tr>\s*</thead>", "", body)   # empty header row
    return (f"<!doctype html><html><head><meta charset='utf-8'><base href='{REPORTS.as_uri()}/'>"
            f"<title>Bedrock research note</title><style>{CSS}</style></head><body>{body}</body></html>")


def render(repo: str | None = None, out: Path = OUT) -> Path:
    from playwright.sync_api import sync_playwright

    html = build_html(SRC.read_text(encoding="utf-8"), repo)
    tmp = REPORTS / "_note_print.html"
    tmp.write_text(html, encoding="utf-8")
    exe = next((b for b in BROWSERS if Path(b).exists()), None) or shutil.which("chrome") or shutil.which("chromium")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            page = browser.new_page()
            page.goto(tmp.as_uri(), wait_until="networkidle")
            page.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True,
                     display_header_footer=True, header_template="<span></span>",
                     footer_template="<div style='font-size:7pt;color:#8a8984;width:100%;text-align:center'>"
                                     "Bedrock · NSE fragility monitor · page <span class='pageNumber'></span> of "
                                     "<span class='totalPages'></span></div>")
            browser.close()
    finally:
        tmp.unlink(missing_ok=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", help="public repo link to print in the header, e.g. github.com/you/bedrock")
    a = ap.parse_args()
    print(f"Saved {render(a.repo)}")
