"""Legge smcp_layout.txt (pdftotext -layout della Ris. A.918(22)) e produce smcp_en.json:
una lista di nodi in ordine: {"t":"h", "id", "titolo", "liv"} per i titoli e {"t":"p", "id", "en", "alt":[...], "liv"} per le frasi.
Le righe "~ ..." sono alternative della frase precedente; le note restano come {"t":"n"}."""
import json, re, sys

src, out = sys.argv[1], sys.argv[2]
righe = open(src, encoding='utf-8').read().split('\n')

# togli intestazioni/piè di pagina e righe vuote ripetute
pul = []
for r in righe:
    if re.search(r'E:\\IMO|I:\\ASSEMBLY', r) or re.match(r'^\s*(A 22/Res\.918\s*)?-\s*\d+\s*-\s*(A 22/Res\.918)?\s*$', r):
        continue
    r = re.sub(r'^(\s*)\.\s+(\d)', r'\1.\2', r)
    pul.append(r.rstrip())

# il corpo inizia dal secondo "GENERAL" (dopo l'indice e l'introduzione)
idx = [i for i, r in enumerate(pul) if r.strip() == 'GENERAL']
inizio_gen = idx[1]
idx_g = [i for i, r in enumerate(pul) if r.strip() == 'GLOSSARY']
inizio_glos = [i for i in idx_g if i > inizio_gen][0]
idx_a = [i for i, r in enumerate(pul) if re.match(r'^\s*PART A\b|^\s*IMO STANDARD MARINE COMMUNICATION PHRASES:\s*PART A', r)]
inizio_a = [i for i in idx_a if i > inizio_glos][0]

json.dump({'general': pul[inizio_gen:inizio_glos], 'glossary': pul[inizio_glos:inizio_a]},
          open(out.replace('.json', '_prosa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

corpo = pul[inizio_a:]
nodi = []
sez = None          # es. "A1/1.1"
sotto = []          # pila di numeri ".1", ".2.1" ... relativi alla sezione
re_sez = re.compile(r'^\s*((?:A[12]|B[1-4])(?:/\d+(?:\.\d+)*)?)\s+([A-Z].*)$')
re_num = re.compile(r'^(\s*)(\.\d+(?:\.\d+)*)\s+(\S.*)$')
re_alt = re.compile(r'^\s*~\s*(.*)$')
fine_frase = re.compile(r'[.?!:"”]\s*$|\.\.\.\s*$')

ultima = None
sub = ''
for i, r in enumerate(corpo):
    if not r.strip():
        ultima = ultima if ultima and ultima['t'] == 'p' else None
        continue
    m = re_sez.match(r)
    if m and not r.strip().startswith('~'):
        sez = m.group(1); sub = ''; ultima = {'t': 'h', 'id': sez, 'titolo': m.group(2).strip(), 'liv': sez.count('/') + sez.count('.')}
        nodi.append(ultima); continue
    m = re_num.match(r)
    if m:
        num, testo = m.group(2), m.group(3).strip()
        # titolo di sottosezione: niente punteggiatura finale e la riga seguente non vuota è più rientrata o è vuota+numero
        succ = next((x for x in corpo[i + 1:i + 4] if x.strip()), '')
        ms = re_num.match(succ)
        titolo = (not fine_frase.search(testo)) and len(testo) < 70 and ms and len(ms.group(1)) > len(m.group(1)) and not testo[0].islower()
        if titolo:
            sub = num
            ultima = {'t': 'h', 'id': (sez or '') + sub, 'titolo': testo, 'liv': 9}
        else:
            ultima = {'t': 'p', 'id': (sez or '') + sub + num, 'en': testo, 'alt': []}
        nodi.append(ultima); continue
    m = re_alt.match(r)
    if m and ultima and ultima['t'] == 'p':
        ultima['alt'].append(m.group(1).strip()); continue
    t = r.strip()
    if ultima and ultima['t'] == 'p':
        if ultima['alt']: ultima['alt'][-1] += ' ' + t
        else: ultima['en'] += ' ' + t
    elif ultima and ultima['t'] == 'n':
        ultima['testo'] += ' ' + t
    else:
        ultima = {'t': 'n', 'id': (sez or '') + '#n', 'testo': t}
        nodi.append(ultima)

for k, x in enumerate(nodi): x['k'] = k
json.dump(nodi, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
p = [n for n in nodi if n['t'] == 'p']; h = [n for n in nodi if n['t'] == 'h']; nn = [n for n in nodi if n['t'] == 'n']
print('titoli', len(h), 'frasi', len(p), 'alternative', sum(len(x['alt']) for x in p), 'note', len(nn))
print('caratteri EN frasi', sum(len(x['en']) + sum(len(a) for a in x['alt']) for x in p))
