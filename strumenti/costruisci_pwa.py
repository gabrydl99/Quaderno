#!/usr/bin/env python3
"""Trasforma l'HTML del Quaderno (come esce dall'artefatto o da unisci.py) in index.html per la PWA.

Uso:
    python3 strumenti/costruisci_pwa.py SORGENTE.html [--versione 1.1] [--sfondo] [--uscita prova.html]

    --sfondo   aggiunge l'immagine dietro agli argomenti della pagina iniziale (img/sfondo-home.jpg)
    --uscita   scrive in un altro file invece di index.html (per le prove)
    --feedback aggiunge segnalazioni e area admin (strumenti/feedback.html, collegamento in strumenti/supabase.json)
    --anteprima non collega Supabase (tutto resta sul telefono: per le prove)
    --data     data dell'aggiornamento da mostrare (gg/mm/aaaa); senza, quella di oggi

Le parti tolte o cambiate su richiesta sono in strumenti/modifiche.json.

Cosa fa (il contenuto degli appunti non viene toccato):
- sostituisce i link agli audio dell'artefatto (/_blob/ID) con i file in audio/ o nel repository Quaderno-Audio,
  secondo strumenti/mappa_audio.json;
- mette i font in locale (fonts/fonts.css) al posto di Google Fonts;
- aggiunge manifest, icone, colore della barra e la registrazione del service worker;
- inserisce la grafica (strumenti/tema.css), il tasto Installa (strumenti/installa.html), i disegni della
  pagina iniziale (strumenti/pagina.html) e le istruzioni aggiornate (strumenti/istruzioni.html);
- aggiorna l'etichetta della versione e il nome della cache in sw.js.
"""
import json, re, sys, pathlib, datetime
from zoneinfo import ZoneInfo

RADICE = pathlib.Path(__file__).resolve().parent.parent
MAPPA = json.loads((RADICE / 'strumenti' / 'mappa_audio.json').read_text(encoding='utf8'))
# MAPPA: { "id_blob": "percorso/file.m4a" }  (percorso relativo a index.html, oppure /Quaderno-audio/...)

TESTA = '''<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Quaderno Patentino</title>
<meta name="description" content="Appunti, disegni e audio delle lezioni per il patentino nautico.">
<meta name="theme-color" content="#f7f9fa" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#05080b" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Quaderno">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png" type="image/png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="stylesheet" href="fonts/fonts.css">
'''

PIEDE = '\n<p class="ver-fondo" title="Versione dell\'app e data dell\'ultimo aggiornamento">Versione <b>{v}</b> · {data}</p>'

REGISTRA = '''
<script>
/* PWA: funziona anche senza internet; gli audio restano sul telefono dopo il primo ascolto */
if ('serviceWorker' in navigator) {
  addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {});
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  });
}
</script>
'''


def costruisci(sorgente: str, versione: str | None, sfondo: bool = False, data: str | None = None, feedback: bool = False, senza_supabase: bool = False) -> str:
    s = sorgente

    # 1. testa dell'artefatto -> testa vera della PWA (lo stile base dell'artefatto resta, per non cambiare l'aspetto)
    m = re.match(r'<!doctype html><html><head><meta charset=utf8><meta name=viewport[^>]*>(<style>.*?</style>)</head><body>', s, re.S)
    if m:
        corpo = re.sub(r'\s*<title>[^<]*</title>', '', s[m.end():], count=1)
        s = TESTA + m.group(1) + '\n</head>\n<body>' + corpo
    s = re.sub(r'\n?<meta name="claude:[^"]*"[^>]*>', '', s)

    # 2. font locali al posto di Google Fonts
    s = re.sub(r'\n?<link rel="preconnect" href="https://fonts\.(googleapis|gstatic)\.com"[^>]*>', '', s)
    s = re.sub(r'\n?<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">', '', s)

    # 3. audio
    mancanti = []
    def sost(mm):
        b = mm.group(1)
        if b not in MAPPA:
            mancanti.append(b)
            return mm.group(0)
        return MAPPA[b]
    s = re.sub(r'/_blob/([0-9a-f]{32})', sost, s)
    if mancanti:
        sys.exit(f'Audio senza file in mappa_audio.json: {sorted(set(mancanti))}')

    # 2b. parti tolte o cambiate su richiesta (strumenti/modifiche.json)
    mod = json.loads((RADICE / 'strumenti' / 'modifiche.json').read_text(encoding='utf8'))
    for g in mod.get('gruppi_da_togliere', []):
        i = s.find(f'<div class="grp" id="{g}"')
        if i < 0:
            sys.exit(f'Gruppo da togliere non trovato: {g}')
        j = s.find('<div class="grp"', i + 10)
        fine_sez = s.find('</section>', i)
        if j < 0 or j > fine_sez:
            # ultimo gruppo della sezione: chiude prima di </section>
            j = s.rfind('</div>', i, fine_sez) + len('</div>')
        s = s[:i] + s[j:]
    for vecchio, nuovo in mod.get('sostituzioni', []):
        if vecchio not in s:
            sys.exit(f'Testo da sostituire non trovato: {vecchio[:60]}')
        s = s.replace(vecchio, nuovo)

    # 3a. istruzioni della pagina iniziale aggiornate (strumenti/istruzioni.html)
    nuove = (RADICE / 'strumenti' / 'istruzioni.html').read_text(encoding='utf8').strip()
    s, n = re.subn(r'<section class="howto".*?</section>', lambda _m: nuove, s, count=1, flags=re.S)
    if not n:
        sys.exit('Istruzioni (section.howto) non trovate nella pagina')

    # 3b. grafica: tema subito dopo lo stile originale, così lo sostituisce dove serve
    tema = (RADICE / 'strumenti' / 'tema.css').read_text(encoding='utf8')
    k = s.find('</style>', s.find('/* Layout')) + len('</style>')
    s = s[:k] + '\n<style id="tema">\n' + tema + '</style>' + s[k:]

    # 4. versione e data dell'ultimo aggiornamento: in fondo alla pagina iniziale, sotto "Come si usa l'app"
    #    (dalla 1.0 del 26/10/2026: 1.0, 1.1, 1.2 … ; prima era in alto a destra come vNN)
    vecchia = re.search(r'class="ver"[^>]*>(v\d+)<', s)
    v = versione or (vecchia.group(1) if vecchia else '')
    s = re.sub(r'\s*<p class="foot-ver">.*?</p>', '', s, count=1, flags=re.S)
    data = data or datetime.datetime.now(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y')
    piede = PIEDE.format(v=v, data=data)
    k = s.find('</section>', s.find('<section class="howto"')) + len('</section>')
    s = s[:k] + piede + s[k:]

    # 5. tasto Installa, immagine di sfondo (facoltativa) e registrazione del service worker
    extra = (RADICE / 'strumenti' / 'installa.html').read_text(encoding='utf8')
    extra += (RADICE / 'strumenti' / 'pagina.html').read_text(encoding='utf8')
    if sfondo:
        extra += (RADICE / 'strumenti' / 'sfondo.html').read_text(encoding='utf8')
    if feedback:
        # profilo (accesso con nome utente, argomenti letti) + segnalazioni e area admin
        fb = (RADICE / 'strumenti' / 'account.html').read_text(encoding='utf8')
        fb += (RADICE / 'strumenti' / 'feedback.html').read_text(encoding='utf8')
        conf = RADICE / 'strumenti' / 'supabase.json'
        c = json.loads(conf.read_text(encoding='utf8')) if conf.exists() and not senza_supabase else {}
        fb = re.sub(r'/\*SUPABASE\*/.*?/\*FINE\*/', lambda _m: json.dumps({'url': c.get('url', ''), 'chiave': c.get('chiave', '')}), fb, flags=re.S)
        extra += fb
    # aggiunte alla pagina iniziale: "Come si usa l'app" compatto, bolla e riquadro del Frasario SMCP
    extra += (RADICE / 'strumenti' / 'home-aggiunte.html').read_text(encoding='utf8')
    s = s.replace('</body></html>', extra + REGISTRA + '</body>\n</html>')
    if REGISTRA not in s:
        s = s.rstrip() + REGISTRA
    return s


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    versione = None
    if '--versione' in sys.argv:
        versione = sys.argv[sys.argv.index('--versione') + 1]
    uscita = sys.argv[sys.argv.index('--uscita') + 1] if '--uscita' in sys.argv else 'index.html'
    src = pathlib.Path(sys.argv[1]).read_text(encoding='utf8')
    data = sys.argv[sys.argv.index('--data') + 1] if '--data' in sys.argv else None
    out = costruisci(src, versione, '--sfondo' in sys.argv, data, '--feedback' in sys.argv, '--anteprima' in sys.argv)
    (RADICE / uscita).write_text(out, encoding='utf8')
    if versione and uscita == 'index.html':
        sw = RADICE / 'sw.js'
        sw.write_text(re.sub(r"const VERSIONE = '[^']*'", f"const VERSIONE = '{versione}'", sw.read_text(encoding='utf8')), encoding='utf8')
    print(uscita, 'scritto', len(out), 'caratteri', '· versione', versione or '(invariata)')


if __name__ == '__main__':
    main()
