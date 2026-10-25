/* Service worker del Quaderno Patentino.
   - Pagina, font e icone: salvati sul telefono, l'app si apre anche senza internet.
   - Pagina: prima prova la rete (così vedi subito gli aggiornamenti), se non c'è usa la copia salvata.
   - Audio: alla prima riproduzione il file viene salvato intero; dopo si ascolta anche offline. */
const VERSIONE = 'v42';
const CACHE = 'qp-app-' + VERSIONE;
const CACHE_AUDIO = 'qp-audio';

const FONT = ['400', '500', '600', '700'].flatMap(w => ['latin', 'latin-ext', 'greek', 'greek-ext'].map(s => `fonts/fira-sans-${s}-${w}-normal.woff2`))
  .concat(['400', '500'].flatMap(w => ['latin', 'latin-ext', 'greek', 'greek-ext'].map(s => `fonts/fira-mono-${s}-${w}-normal.woff2`)));
const BASE = ['./', 'manifest.webmanifest', 'fonts/fonts.css', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png', 'img/sfondo-home.jpg', 'assetto/', 'carteggio/', 'fonts/esercizi.css', ...FONT];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(BASE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE && k !== CACHE_AUDIO) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.endsWith('.m4a')) { e.respondWith(audio(e)); return; }
  if (req.mode === 'navigate') { e.respondWith(pagina(req)); return; }
  e.respondWith(caches.match(req, {ignoreSearch: true}).then(hit => hit || fetch(req).then(r => {
    if (r.ok) { const copia = r.clone(); caches.open(CACHE).then(c => c.put(req, copia)); }
    return r;
  })));
});

/* pagina: rete con attesa massima di 4 s, poi la copia salvata */
async function pagina(req) {
  const cache = await caches.open(CACHE);
  try {
    const chiave = new URL(req.url).pathname.endsWith('/index.html') ? './' : req.url.split('#')[0];
    const rete = fetch(req).then(r => { if (r.ok) cache.put(chiave, r.clone()); return r; });
    const r = await Promise.race([rete, new Promise((_, no) => setTimeout(() => no(new Error('lenta')), 4000))]);
    return r;
  } catch (err) {
    return (await cache.match(req, {ignoreSearch: true})) || (await cache.match('./')) || fetch(req);
  }
}

/* audio: risponde dalla copia salvata (anche a pezzi, come vuole il lettore); altrimenti dalla rete e intanto lo salva */
const inCorso = new Map();
async function audio(e) {
  const req = e.request;
  const chiave = req.url.split('#')[0].split('?')[0];
  const cache = await caches.open(CACHE_AUDIO);
  const hit = await cache.match(chiave);
  if (hit) return aPezzi(hit, req.headers.get('range'));
  if (!inCorso.has(chiave)) {
    const p = fetch(chiave).then(r => (r.ok && r.status === 200) ? cache.put(chiave, r) : null)
      .catch(() => {}).finally(() => inCorso.delete(chiave));
    inCorso.set(chiave, p);
    e.waitUntil(p);
  }
  return fetch(req);
}

async function aPezzi(resp, range) {
  if (!range) return resp;
  const blob = await resp.blob(), n = blob.size;
  const m = /bytes=(\d*)-(\d*)/.exec(range);
  let da = 0, a = n - 1;
  if (m) {
    if (m[1] === '' && m[2] !== '') { da = Math.max(0, n - +m[2]); }
    else { da = +m[1] || 0; if (m[2] !== '') a = Math.min(+m[2], n - 1); }
  }
  if (da >= n) return new Response(null, {status: 416, headers: {'Content-Range': `bytes */${n}`}});
  return new Response(blob.slice(da, a + 1), {
    status: 206,
    headers: {
      'Content-Type': resp.headers.get('Content-Type') || 'audio/mp4',
      'Content-Range': `bytes ${da}-${a}/${n}`,
      'Content-Length': String(a - da + 1),
      'Accept-Ranges': 'bytes'
    }
  });
}
