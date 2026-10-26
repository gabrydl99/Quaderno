"""Unisce testo inglese, traduzioni e glossari in dati.json (per la pagina) e nei file TSV per DeepL (scritti accanto a dati.json).
Uso: python3 strumenti/frasario/build_dati.py frasario/dati.json"""
import json, re, glob, sys, importlib.util, os
QUI = os.path.dirname(os.path.abspath(__file__))
def carica(nome):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(QUI, nome + '.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

nodi = json.load(open(os.path.join(QUI, 'smcp_en.json'), encoding='utf-8'))
tav = json.load(open(os.path.join(QUI, 'tavole.json'), encoding='utf-8'))

it = {}
for f in sorted(glob.glob(os.path.join(QUI, 'it_*.txt'))):
    for r in open(f, encoding='utf-8'):
        r = r.rstrip('\n')
        if not r.strip(): continue
        k, _, t = r.partition('|')
        it[k] = t

# correzioni dell'inglese (testi del PDF uniti male)
EN_FIX = {2503: 'Everyone, please, be quiet. The children / the sick need rest.'}

out = []
mancano = []
for x in nodi:
    k = x['k']
    if k in tav['togli']: continue
    if str(k) in tav['tab']:
        out.append({'t': 'tab', 'id': x['id'], 'tab': tav['tab'][str(k)]}); continue
    if x['t'] == 'h':
        e = x['titolo']; t = it.get(str(k))
        if t is None: mancano.append(k)
        out.append({'t': 'h', 'id': x['id'], 'en': e, 'it': t or ''})
    elif x['t'] == 'n':
        t = it.get(str(k));
        if t is None: mancano.append(k)
        out.append({'t': 'n', 'id': x['id'], 'en': EN_FIX.get(k, x['testo']), 'it': t or ''})
    else:
        t = it.get(str(k))
        if t is None: mancano.append(k)
        alt = []
        for i, a in enumerate(x['alt']):
            ta = it.get(f'{k}~{i}')
            if ta is None: mancano.append(f'{k}~{i}')
            alt.append([a, ta or ''])
        out.append({'t': 'p', 'id': x['id'], 'en': EN_FIX.get(k, x['en']), 'it': t or '', 'alt': alt})
extra = set(it) - {str(x['k']) for x in nodi} - {f"{x['k']}~{i}" for x in nodi if x['t'] == 'p' for i in range(len(x['alt']))}
print('mancano', len(mancano), mancano[:20], '| in più', sorted(extra)[:10])
# segnaposto "@" = sostituito da tabella
out = [o for o in out if not (o.get('it') == '@' and o['t'] != 'tab')]

# sezione GENERAL davanti
gen = carica('generale').G
gnodi = []
for tipo, ident, en, itx in gen:
    if tipo == 'tab': gnodi.append({'t': 'tab', 'id': ident, 'tab': en})
    elif tipo == 'p': gnodi.append({'t': 'p', 'id': ident, 'en': en, 'it': itx, 'alt': []})
    else: gnodi.append({'t': tipo, 'id': ident, 'en': en, 'it': itx})

# id univoci per i collegamenti
visti = {}
for o in gnodi + out:
    b = o['id']; visti[b] = visti.get(b, 0) + 1
    o['u'] = b if visti[b] == 1 else f'{b}~{visti[b]}'

# ---------- glossario ----------
gs = carica('glos_smcp_it')
voci_en = json.load(open(os.path.join(QUI, 'glos_smcp_en.json'), encoding='utf-8'))
glos = []
for v in voci_en:
    if v['en'] in gs.TOGLI_EN: continue
    de = gs.CORREZIONI_EN.get(v['en'], v['def'])
    if v['en'] not in gs.IT: print('glossario SMCP senza traduzione:', v['en']); continue
    t, d = gs.IT[v['en']]
    glos.append({'en': v['en'], 'it': t, 'd': d, 'de': de, 'c': 'SMCP' if v['parte'].startswith('1') else 'SMCP · VTS', 's': 1})
for nome in gs.CORREZIONI_EN:
    if nome not in {g['en'] for g in glos}:
        t, d = gs.IT[nome]; glos.append({'en': nome, 'it': t, 'd': d, 'de': gs.CORREZIONI_EN[nome], 'c': 'SMCP', 's': 1})
gia = {g['en'].lower() for g in glos}
for r in open(os.path.join(QUI, 'glos_extra.txt'), encoding='utf-8'):
    if r.startswith('#') or not r.strip(): continue
    p = [c.strip() for c in r.rstrip('\n').split('|')]
    en, itx, cat, d = p[0], p[1], p[2], p[3]
    x = len(p) > 4 and p[4] == 'x'
    if en.lower() in gia: continue
    gia.add(en.lower())
    o = {'en': en, 'it': itx, 'd': d, 'c': cat}
    if x: o['x'] = 1
    glos.append(o)
NO_DEEPL_SMCP = {'List','Berth','Cable','Check (to)','Station','Target','Track','Transit','Datum','Blast','Hoist','Launch (to)','Briefing','Scene','Operational','Located','Reported','Disabled','Recover (to)','Resume (to)','Proceed (to)','Drifting','Leaking','Inoperative','Destination','Escort','Let go (to)','Stand by (to)','Shackle','Slings','Course','Heading','Overflow','Spill','Casualty'}
for g in glos:
    if g.get('s') and g['en'] in NO_DEEPL_SMCP: g['x'] = 1
glos.sort(key=lambda g: re.sub(r'^\W+', '', g['en']).lower())

# ---------- glossari per DeepL ----------
def pulisci_en(s):
    s = re.sub(r'\s*\((to|of [^)]*|D|or draft)\)', '', s).strip()
    s = s.split(' / ')[0].split('/')[0].strip()
    return s
def pulisci_it(s):
    if re.search(r'\d\)', s): return ''
    s = re.sub(r'\s*\([^)]*\)', '', s).strip()
    s = s.split(', ')[0].strip()
    return s
en_it, it_en = {}, {}
for g in glos:
    if g.get('x'): continue
    e, i = pulisci_en(g['en']), pulisci_it(g['it'])
    if not e or not i or len(e) < 3: continue
    if e.isupper() and len(e) <= 6: continue          # sigle: restano uguali
    if e.lower() not in en_it: en_it[e.lower()] = (e, i)
    if i.lower() not in it_en: it_en[i.lower()] = (i, e)
def tsv(d): return '\n'.join(f'{a}\t{b}' for a, b in d.values() if '\t' not in a + b)

dati = {'v': 1, 'fonte': 'IMO Res. A.918(22) – IMO Standard Marine Communication Phrases',
        'nodi': gnodi + out, 'glos': glos}
uscita = sys.argv[1] if len(sys.argv) > 1 else os.path.join(QUI, 'dati.json')
json.dump(dati, open(uscita, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
cart = os.path.dirname(os.path.abspath(uscita))
open(os.path.join(cart, 'deepl_en_it.tsv'), 'w', encoding='utf-8').write(tsv(en_it))
open(os.path.join(cart, 'deepl_it_en.tsv'), 'w', encoding='utf-8').write(tsv(it_en))
print('nodi', len(dati['nodi']), 'frasi', sum(1 for n in dati['nodi'] if n['t'] == 'p'), 'glossario', len(glos),
      'deepl en>it', len(en_it), 'it>en', len(it_en), 'byte', os.path.getsize(uscita))
