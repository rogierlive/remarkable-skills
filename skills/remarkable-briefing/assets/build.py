"""Zet een briefing in markdown om naar HTML. Gebruik: build.py bron.md uit.html [paginas-json]"""
import html as htmllib, os, re, sys, json, markdown, pathlib

src = pathlib.Path(sys.argv[1]).read_text()
out = pathlib.Path(sys.argv[2])
pages = json.loads(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else {}

m = re.match(r"^---\n(.*?)\n---\n", src, flags=re.S)
title = "Briefing"
if m:
    t = re.search(r"^titel:\s*(.+)$", m.group(1), flags=re.M)
    if t: title = t.group(1).strip().strip('"')
src = re.sub(r"^---\n.*?\n---\n", "", src, flags=re.S)
for i in range(1, 15):
    src = src.replace("{p%d}" % i, str(pages.get(str(i), "")))
src = src.replace("{pb}", str(pages.get("b", "")))
src = src.replace("{naam}", os.environ.get("REMARKABLE_NAAM", "jou"))

html = markdown.markdown(src, extensions=["tables", "md_in_html", "attr_list"])

css = r"""
@page { size: 210mm 280mm; margin: 17mm 17mm 18mm 17mm;
  @bottom-center { content: counter(page); font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 9pt; color: #666; } }
@page :first { @bottom-center { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; }
body { font-family: Charter, 'Iowan Old Style', Georgia, serif; font-size: 12.5pt; line-height: 1.45; color: #000; background: #fff; margin: 0; }
h1, h2, h3, .kicker, .lt, th, .lbl, .date { font-family: 'Helvetica Neue', Arial, sans-serif; }
h2 { font-size: 21pt; margin: 0 0 8pt; padding-bottom: 5pt; border-bottom: 1.5pt solid #000; }
h3 { font-size: 13.5pt; margin: 16pt 0 5pt; break-after: avoid; }
p { margin: 0 0 8pt; }
ul, ol { margin: 0 0 8pt; padding-left: 18pt; }
li { margin-bottom: 3pt; }
.pb { break-after: page; height: 0; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0 10pt; font-size: 10.5pt; line-height: 1.3; break-inside: avoid; }
th { text-align: left; font-size: 9.5pt; border-bottom: 1.2pt solid #000; padding: 4pt 5pt; }
td { border-bottom: 0.5pt solid #999; padding: 4pt 5pt; vertical-align: top; }
.small table, .small { font-size: 9.5pt; }
.small li { margin-bottom: 1pt; }
code { font-family: Menlo, monospace; font-size: 8pt; word-break: break-all; }
.box { border: 1pt solid #000; padding: 9pt 12pt 4pt; margin: 10pt 2pt 10pt 0; break-inside: avoid; }
.note { border-left: 3pt solid #555; padding: 4pt 10pt; margin: 10pt 0; font-size: 11pt; color: #222; }
.quote { font-size: 14pt; font-style: italic; border-top: 0.8pt solid #000; border-bottom: 0.8pt solid #000; padding: 8pt 4pt; margin: 12pt 0; }
.cover { padding-top: 30mm; }
.kicker { font-size: 11pt; letter-spacing: 1pt; text-transform: uppercase; color: #444; margin-bottom: 10pt; }
.title { font-size: 38pt; line-height: 1.05; margin: 0 0 14pt; }
.sub { font-size: 15pt; color: #333; max-width: 140mm; }
.date { font-size: 13pt; margin: 18pt 0 30mm; padding-top: 8pt; border-top: 1.5pt solid #000; width: 60mm; }
.toc table { font-size: 14pt; }
.toc td { padding: 7pt 5pt; }
.toc td:first-child { width: 12mm; font-weight: bold; font-family: 'Helvetica Neue', Arial, sans-serif; }
.toc td:last-child { text-align: right; width: 15mm; }
.toc thead { display: none; }
.layers { margin: 8pt 0 12pt; }
.layer { border: 1.5pt solid #000; padding: 6pt 12pt 0; } .layer ul { margin-bottom: 4pt; } .layer p { margin-bottom: 4pt; }
.layer:first-child { border-style: dashed; }
.lt { font-weight: bold; font-size: 12.5pt; margin-bottom: 4pt; }
.pay { font-style: italic; border-top: 0.5pt solid #999; padding-top: 4pt; }
.arrow { text-align: center; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; color: #444; padding: 3pt 0; }
.arrow::before { content: "▲  "; } .arrow::after { content: "  ▲"; }
.cb { display: inline-block; width: 10pt; height: 10pt; border: 1.2pt solid #000; vertical-align: -1pt; margin-right: 4pt; }
.choices ol { padding-left: 20pt; } .choices li { margin-bottom: 6pt; font-size: 11.5pt; }
.checklist p { margin: 5pt 0 0; font-size: 11pt; } .checklist .line { height: 19pt; }
.line { border-bottom: 0.7pt solid #777; height: 22pt; }
.sheet table { font-size: 11pt; } .sheet td { height: 30pt; border-bottom: 0.7pt solid #777; }
.sheet td:first-child { width: 42%; } .sheet th { font-size: 10pt; }
.sheet td + td { border-left: 0.5pt solid #bbb; }
.field { border-bottom: 0.7pt solid #777; height: 40pt; padding-top: 4pt; }
.lbl { font-weight: bold; font-size: 11pt; } .hint { font-size: 9.5pt; color: #555; font-style: italic; margin-left: 6pt; }
"""
out.write_text(f"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src file: data:; font-src file: data:"><title>{htmllib.escape(title)}</title><style>{css}</style></head><body>{html}</body></html>""")
