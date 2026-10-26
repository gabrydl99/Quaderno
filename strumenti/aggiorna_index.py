#!/usr/bin/env python3
"""Aggiorna index.html senza ricostruirlo dal sorgente dell'artefatto: sostituisce le parti di strumenti/
cambiate dall'ultimo commit (account, feedback, tema, istruzioni, …) e mette versione e data in fondo.

Uso:
    python3 strumenti/aggiorna_index.py --versione 1.1 [--data 27/10/2026]

Versioni dalla 1.0 (26/10/2026): 1.0, 1.1, 1.2 … (2.0 solo per cambi grossi). Aggiorna anche sw.js.
Confronta con l'ultimo commit: per rilanciarlo dopo altre modifiche (senza commit in mezzo) prima
`git checkout index.html sw.js`.
"""
import json, re, subprocess, sys, pathlib, datetime
from zoneinfo import ZoneInfo

RADICE = pathlib.Path(__file__).resolve().parent.parent
PARTI = ['tema.css', 'istruzioni.html', 'installa.html', 'pagina.html', 'sfondo.html', 'account.html', 'feedback.html', 'home-aggiunte.html']
sys.path.insert(0, str(RADICE / 'strumenti'))
from costruisci_pwa import PIEDE  # noqa: E402


def con_supabase(t: str) -> str:
    c = json.loads((RADICE / 'strumenti' / 'supabase.json').read_text(encoding='utf8'))
    return re.sub(r'/\*SUPABASE\*/.*?/\*FINE\*/', lambda _m: json.dumps({'url': c['url'], 'chiave': c['chiave']}), t, flags=re.S)


def main():
    if '--versione' not in sys.argv:
        sys.exit(__doc__)
    v = sys.argv[sys.argv.index('--versione') + 1]
    data = sys.argv[sys.argv.index('--data') + 1] if '--data' in sys.argv else datetime.datetime.now(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y')
    idx = RADICE / 'index.html'
    s = idx.read_text(encoding='utf8')
    for f in PARTI:
        nuovo = con_supabase((RADICE / 'strumenti' / f).read_text(encoding='utf8'))
        vecchio = subprocess.run(['git', '-C', str(RADICE), 'show', 'HEAD:strumenti/' + f], capture_output=True, text=True, check=True).stdout
        vecchio = con_supabase(vecchio)
        if vecchio == nuovo:
            continue
        if vecchio in s:
            s = s.replace(vecchio, nuovo, 1)
        elif vecchio.strip() in s:
            s = s.replace(vecchio.strip(), nuovo.strip(), 1)
        else:
            sys.exit(f'{f}: la versione vecchia non si trova in index.html (ricostruisci con costruisci_pwa.py)')
        print('aggiornato', f)
    # versione: niente più in alto (fino alla v47), in fondo alla pagina iniziale
    s = re.sub(r'<span class="ver-top"[^>]*>.*?</small></span>\s*', '', s, count=1, flags=re.S)
    piede = PIEDE.format(v=v, data=data)
    if 'class="ver-fondo"' in s:
        s = re.sub(r'\n?<p class="ver-fondo"[^>]*>.*?</p>', piede, s, count=1, flags=re.S)
    else:
        k = s.find('</section>', s.find('<section class="howto"')) + len('</section>')
        s = s[:k] + piede + s[k:]
    idx.write_text(s, encoding='utf8')
    sw = RADICE / 'sw.js'
    sw.write_text(re.sub(r"const VERSIONE = '[^']*'", f"const VERSIONE = '{v}'", sw.read_text(encoding='utf8')), encoding='utf8')
    print('index.html e sw.js: versione', v, data)


if __name__ == '__main__':
    main()
