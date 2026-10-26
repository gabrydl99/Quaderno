// Funzione "traduci" del Quaderno Patentino: traduzione DeepL con il glossario nautico del Frasario SMCP.
// - Solo per chi ha fatto l'accesso nell'app (token dell'utente verificato su Supabase Auth).
// - Massimo 300 caratteri per richiesta, massimo 30 richieste ogni 10 minuti per utente.
// - La chiave DeepL resta qui, nel segreto DEEPL_KEY: l'app non la vede mai.
// - GET ?stato=1 : controllo (chiave presente, uso del mese, glossario pronto) senza tradurre nulla.
// Il glossario sta nel sito dell'app (frasario/deepl_en_it.tsv e deepl_it_en.tsv): se cambia, qui si crea da solo il nuovo glossario DeepL.
const SITO = "https://gabrydl99.github.io/Quaderno/frasario/";

const MAX_CARATTERI = 300;
const LIMITE = 30, FINESTRA_MS = 10 * 60 * 1000;
const ORIGINI = [/^https:\/\/gabrydl99\.github\.io$/, /^http:\/\/localhost(:\d+)?$/, /^http:\/\/127\.0\.0\.1(:\d+)?$/];

const chiave = () => Deno.env.get("DEEPL_KEY") ?? "";
const base = () => (chiave().endsWith(":fx") ? "https://api-free.deepl.com" : "https://api.deepl.com");
const dl = (percorso: string, init: RequestInit = {}) =>
  fetch(base() + percorso, { ...init, headers: { Authorization: "DeepL-Auth-Key " + chiave(), "Content-Type": "application/json", ...(init.headers ?? {}) } });

function cors(req: Request) {
  const o = req.headers.get("origin") ?? "";
  const h: Record<string, string> = {
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Vary": "Origin",
  };
  if (ORIGINI.some((r) => r.test(o))) h["Access-Control-Allow-Origin"] = o;
  return h;
}
const json = (req: Request, corpo: unknown, stato = 200) =>
  new Response(JSON.stringify(corpo), { status: stato, headers: { ...cors(req), "Content-Type": "application/json" } });

/* glossario: UN solo glossario DeepL "multilingue" (API v3) con le due direzioni EN>IT e IT>EN.
   Il piano Free accetta pochi glossari, quindi prima di crearne uno nuovo si cancellano i vecchi "qp-smcp-".
   I TSV vengono dal sito; il nome contiene un'impronta del contenuto, così una modifica crea il glossario nuovo. */
let glos: { id: string; quando: number } | null = null;
async function impronta(t: string) {
  const h = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(t));
  return [...new Uint8Array(h)].slice(0, 5).map((b) => b.toString(16).padStart(2, "0")).join("");
}
async function glossario(): Promise<string | null> {
  if (glos && Date.now() - glos.quando < 6 * 3600 * 1000) return glos.id;     // ricontrolla il sito ogni 6 ore
  const [f1, f2] = await Promise.all([fetch(SITO + "deepl_en_it.tsv", { cache: "no-store" }), fetch(SITO + "deepl_it_en.tsv", { cache: "no-store" })]);
  if (!f1.ok || !f2.ok) { console.error("tsv", f1.status, f2.status); return glos?.id ?? null; }
  const enIt = (await f1.text()).trim(), itEn = (await f2.text()).trim();
  const nome = "qp-smcp-" + await impronta(enIt + "\n#\n" + itEn);
  const r = await dl("/v3/glossaries");
  const lista: { name: string; glossary_id: string }[] = r.ok ? ((await r.json()).glossaries ?? []) : [];
  const g = lista.find((x) => x.name === nome);
  if (g) { glos = { id: g.glossary_id, quando: Date.now() }; return g.glossary_id; }
  for (const v of lista) if (v.name.startsWith("qp-smcp-")) await dl("/v3/glossaries/" + v.glossary_id, { method: "DELETE" });   // toglie le versioni vecchie
  const r2 = await dl("/v2/glossaries");                                                                                           // e quelle create con l'API v2
  if (r2.ok) for (const v of ((await r2.json()).glossaries ?? []) as { name: string; glossary_id: string }[])
    if (v.name.startsWith("qp-smcp-")) await dl("/v2/glossaries/" + v.glossary_id, { method: "DELETE" });
  const n = await dl("/v3/glossaries", {
    method: "POST",
    body: JSON.stringify({ name: nome, dictionaries: [
      { source_lang: "en", target_lang: "it", entries: enIt, entries_format: "tsv" },
      { source_lang: "it", target_lang: "en", entries: itEn, entries_format: "tsv" },
    ] }),
  });
  if (!n.ok) { console.error("glossario", nome, n.status, await n.text()); return null; }
  const id = (await n.json()).glossary_id;
  glos = { id, quando: Date.now() };
  return id;
}

/* utente: il token dell'app deve essere valido */
async function utente(req: Request): Promise<string | null> {
  const auth = req.headers.get("authorization") ?? "";
  if (!auth.startsWith("Bearer ")) return null;
  const apikey = req.headers.get("apikey") ?? Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  const r = await fetch(Deno.env.get("SUPABASE_URL") + "/auth/v1/user", { headers: { Authorization: auth, apikey } });
  if (!r.ok) return null;
  const u = await r.json();
  return u?.id ?? null;
}

const usi = new Map<string, number[]>();
function troppe(id: string) {
  const ora = Date.now(), l = (usi.get(id) ?? []).filter((t) => ora - t < FINESTRA_MS);
  if (l.length >= LIMITE) { usi.set(id, l); return true; }
  l.push(ora); usi.set(id, l); return false;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(req) });
  const url = new URL(req.url);

  if (req.method === "GET" && url.searchParams.has("stato")) {
    if (!chiave()) return json(req, { chiave: false });
    const u = await dl("/v2/usage");
    const uso = u.ok ? await u.json() : null;
    const g = await glossario();
    return json(req, { chiave: u.ok, piano: chiave().endsWith(":fx") ? "free" : "pro", uso, glossario: !!g });
  }
  if (req.method !== "POST") return json(req, { errore: "metodo" }, 405);

  const id = await utente(req);
  if (!id) return json(req, { errore: "accesso", messaggio: "Per la traduzione DeepL serve l'accesso con il tuo account." }, 401);
  if (!chiave()) return json(req, { errore: "chiave", messaggio: "DeepL non è ancora configurato." }, 503);
  if (troppe(id)) return json(req, { errore: "limite", messaggio: "Troppe richieste: riprova tra qualche minuto." }, 429);

  let corpo: { testo?: string; da?: string };
  try { corpo = await req.json(); } catch { return json(req, { errore: "formato" }, 400); }
  const testo = (corpo.testo ?? "").trim();
  const da = corpo.da === "en" ? "en" : "it";
  if (!testo) return json(req, { errore: "vuoto" }, 400);
  if (testo.length > MAX_CARATTERI) return json(req, { errore: "lungo", messaggio: `Massimo ${MAX_CARATTERI} caratteri.` }, 400);

  let gid = await glossario();
  const traduci = (g: string | null) => dl("/v2/translate", {
    method: "POST",
    body: JSON.stringify({
      text: [testo], source_lang: da.toUpperCase(), target_lang: da === "en" ? "IT" : "EN-GB",
      ...(g ? { glossary_id: g } : {}),
    }),
  });
  let r = await traduci(gid);
  if (gid && (r.status === 400 || r.status === 404)) { console.error("glossario rifiutato", r.status, await r.text()); gid = null; r = await traduci(null); }
  if (r.status === 456) return json(req, { errore: "quota", messaggio: "Caratteri DeepL del mese finiti." }, 503);
  if (!r.ok) { console.error("translate", r.status, await r.text()); return json(req, { errore: "deepl", messaggio: "DeepL non risponde: riprova." }, 502); }
  const j = await r.json();
  return json(req, { traduzione: j.translations?.[0]?.text ?? "", da, a: da === "en" ? "it" : "en", glossario: !!gid });
});
