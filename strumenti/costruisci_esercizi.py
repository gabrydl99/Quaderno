#!/usr/bin/env python3
"""Trasforma una pagina di esercizi (HTML scaricato dall'artefatto) in una pagina a parte del Quaderno.

Uso:
    python3 strumenti/costruisci_esercizi.py SORGENTE.html CARTELLA "Titolo"
    es. python3 strumenti/costruisci_esercizi.py assetto.html assetto "Assetto e pescaggi"

Il contenuto della pagina non viene toccato. Aggiunge solo:
- l'intestazione vera (titolo, icone, manifest dell'app);
- in cima, la barra "‹ Quaderno Patentino" per tornare all'app;
- lo stesso tema chiaro/scuro scelto nel Quaderno e il funzionamento senza internet.
"""
import re, sys, pathlib

RADICE = pathlib.Path(__file__).resolve().parent.parent

TESTA = '''<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{titolo} · Quaderno Patentino</title>
<meta name="theme-color" content="#f7f9fa" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#05080b" media="(prefers-color-scheme: dark)">
<link rel="manifest" href="../manifest.webmanifest">
<link rel="icon" href="../icons/icon-192.png" type="image/png">
<link rel="apple-touch-icon" href="../icons/apple-touch-icon.png">
<script>
/* stesso tema (chiaro/scuro) scelto nel Quaderno */
try {{ var t = localStorage.getItem('qp-theme'); if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; }} catch (e) {{}}
</script>
'''

BARRA = '''<style id="qp-torna-css">
.qp-torna{position:relative;z-index:2;display:flex;align-items:center;gap:10px;padding:8px max(14px,env(safe-area-inset-right,0px)) 8px max(14px,env(safe-area-inset-left,0px));
  background:rgba(234,242,247,.92);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-bottom:1px solid #cdd9e3;font:600 15px/1.2 "Fira Sans","Segoe UI",Roboto,Arial,sans-serif}
.qp-torna a{flex:none;white-space:nowrap;box-sizing:border-box;font:inherit;display:inline-flex;align-items:center;gap:7px;min-height:36px;padding:0 12px 0 8px;border-radius:999px;border:1.5px solid #cdd9e3;background:#fff;color:#0c1b2b;text-decoration:none}
.qp-torna a:focus-visible{outline:2px solid #0a4cab;outline-offset:2px}
.qp-torna svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.qp-torna span{color:#43576a;font-weight:500;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .qp-torna{background:rgba(6,17,27,.9);border-bottom-color:#24394c}
  :root:not([data-theme="light"]) .qp-torna a{background:#0c1a27;border-color:#24394c;color:#eef4f9}:root:not([data-theme="light"]) .qp-torna span{color:#a8bccc}}
:root[data-theme="dark"] .qp-torna{background:rgba(6,17,27,.9);border-bottom-color:#24394c}
:root[data-theme="dark"] .qp-torna a{background:#0c1a27;border-color:#24394c;color:#eef4f9}
:root[data-theme="dark"] .qp-torna span{color:#a8bccc}
</style>
<nav class="qp-torna" aria-label="Quaderno Patentino"><a href="../"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14.5 5.5 8 12l6.5 6.5"/></svg>Quaderno Patentino</a><span>{titolo}</span></nav>
'''

REGISTRA = '''
<script>
if ('serviceWorker' in navigator) addEventListener('load', () => { navigator.serviceWorker.register('../sw.js').catch(() => {}); });
</script>
'''


def costruisci(src: str, titolo: str) -> str:
    m = re.match(r'<!doctype html><html><head><meta charset=utf8><meta name=viewport[^>]*>(<style>.*?</style>)</head><body>\s*', src, re.S)
    if not m:
        sys.exit('Formato della pagina non riconosciuto')
    corpo = src[m.end():]
    corpo = re.sub(r'^\s*<title>[^<]*</title>\s*', '', corpo, count=1)
    corpo = re.sub(r'\n?<meta name="claude:[^"]*"[^>]*>', '', corpo)
    # caratteri in locale (../fonts/esercizi.css) al posto di Google Fonts, per l'uso senza internet
    corpo = re.sub(r'\n?<link rel="preconnect" href="https://fonts\.(googleapis|gstatic)\.com"[^>]*>', '', corpo)
    corpo, n = re.subn(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">', '<link rel="stylesheet" href="../fonts/esercizi.css">', corpo)
    # i tag <link>/<style> iniziali della pagina restano nel corpo come nell'artefatto (funzionano anche lì)
    s = TESTA.format(titolo=titolo) + m.group(1) + '\n</head>\n<body>\n' + BARRA.replace('{titolo}', titolo) + corpo
    s = s.replace('</body></html>', REGISTRA + '</body>\n</html>')
    if REGISTRA not in s:
        s = s.rstrip() + REGISTRA
    return s


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1]).read_text(encoding='utf8')
    out = RADICE / sys.argv[2] / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(costruisci(src, sys.argv[3]), encoding='utf8')
    print(out.relative_to(RADICE), 'scritto')


if __name__ == '__main__':
    main()
