// Funzione "traduci" del Quaderno Patentino: traduzione DeepL con il glossario nautico del Frasario SMCP,
// e traduzione tecnica con Gemini per gli account abilitati.
// - Solo per chi ha fatto l'accesso nell'app (token dell'utente verificato su Supabase Auth).
// - Massimo 300 caratteri per richiesta, massimo 30 richieste ogni 10 minuti per utente.
// - Le chiavi restano qui, nei segreti DEEPL_KEY e GEMINI_KEY: l'app non le vede mai.
// - Gemini solo per gli account con app_metadata.ruolo = 'admin' oppure app_metadata.gemini = true
//   (la registrazione è libera: Gemini non si apre da solo ai nuovi account). Modello: segreto GEMINI_MODEL, se c'è,
//   altrimenti il miglior "flash" disponibile con la chiave.
// - GET ?stato=1 : controllo (chiavi presenti, uso DeepL del mese, glossario pronto, modello Gemini) senza tradurre nulla.
// - POST {controllo: true} : dice all'app se l'account può usare Gemini.
// Il glossario sta nel sito dell'app (frasario/deepl_en_it.tsv e deepl_it_en.tsv): se cambia, qui si crea da solo il nuovo glossario DeepL,
// e gli stessi termini vengono passati a Gemini quando compaiono nella frase.
const SITO = "https://gabrydl99.github.io/Quaderno/frasario/";
const GEM = "https://generativelanguage.googleapis.com/v1beta";

const MAX_CARATTERI = 300;
const LIMITE = 30, FINESTRA_MS = 10 * 60 * 1000;
const ORIGINI = [/^https:\/\/gabrydl99\.github\.io$/, /^http:\/\/localhost(:\d+)?$/, /^http:\/\/127\.0\.0\.1(:\d+)?$/];

const chiave = () => Deno.env.get("DEEPL_KEY") ?? "";
const gkey = () => Deno.env.get("GEMINI_KEY") ?? "";
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

/* TSV del glossario dal sito (ricontrollati ogni 6 ore): usati per il glossario DeepL e per i termini da passare a Gemini */
let fonte: { enIt: string; itEn: string; quando: number } | null = null;
async function tsv() {
  if (fonte && Date.now() - fonte.quando < 6 * 3600 * 1000) return fonte;
  const [f1, f2] = await Promise.all([fetch(SITO + "deepl_en_it.tsv", { cache: "no-store" }), fetch(SITO + "deepl_it_en.tsv", { cache: "no-store" })]);
  if (!f1.ok || !f2.ok) { console.error("tsv", f1.status, f2.status); return fonte; }
  fonte = { enIt: (await f1.text()).trim(), itEn: (await f2.text()).trim(), quando: Date.now() };
  return fonte;
}

/* glossario: UN solo glossario DeepL "multilingue" (API v3) con le due direzioni EN>IT e IT>EN.
   Il piano Free accetta pochi glossari, quindi prima di crearne uno nuovo si cancellano i vecchi "qp-smcp-".
   Il nome contiene un'impronta del contenuto, così una modifica crea il glossario nuovo. */
let glos: { id: string; quando: number } | null = null;
async function impronta(t: string) {
  const h = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(t));
  return [...new Uint8Array(h)].slice(0, 5).map((b) => b.toString(16).padStart(2, "0")).join("");
}
async function glossario(): Promise<string | null> {
  if (glos && Date.now() - glos.quando < 6 * 3600 * 1000) return glos.id;     // ricontrolla il sito ogni 6 ore
  const f = await tsv();
  if (!f) return glos?.id ?? null;
  const { enIt, itEn } = f;
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

/* utente: il token dell'app deve essere valido; dall'account si legge anche se può usare Gemini */
async function utente(req: Request): Promise<{ id: string; gemini: boolean } | null> {
  const auth = req.headers.get("authorization") ?? "";
  if (!auth.startsWith("Bearer ")) return null;
  const apikey = req.headers.get("apikey") ?? Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  const r = await fetch(Deno.env.get("SUPABASE_URL") + "/auth/v1/user", { headers: { Authorization: auth, apikey } });
  if (!r.ok) return null;
  const u = await r.json();
  if (!u?.id) return null;
  const m = u.app_metadata ?? {};
  return { id: u.id, gemini: m.ruolo === "admin" || m.gemini === true };
}

const usi = new Map<string, number[]>();
function troppe(id: string) {
  const ora = Date.now(), l = (usi.get(id) ?? []).filter((t) => ora - t < FINESTRA_MS);
  if (l.length >= LIMITE) { usi.set(id, l); return true; }
  l.push(ora); usi.set(id, l); return false;
}

/* ---------- Gemini ---------- */
let modelloScelto: { nome: string; quando: number } | null = null;
async function modello(): Promise<string | null> {
  const fisso = Deno.env.get("GEMINI_MODEL");
  if (fisso) return fisso;
  if (modelloScelto && Date.now() - modelloScelto.quando < 24 * 3600 * 1000) return modelloScelto.nome;
  const r = await fetch(GEM + "/models?pageSize=200", { headers: { "x-goog-api-key": gkey() } });
  if (!r.ok) { console.error("modelli", r.status, await r.text()); return modelloScelto?.nome ?? null; }
  const lista: string[] = ((await r.json()).models ?? [])
    .filter((m: { name: string; supportedGenerationMethods?: string[] }) =>
      /flash/i.test(m.name) && !/image|tts|audio|live|embed|omni/i.test(m.name) &&
      (m.supportedGenerationMethods ?? []).includes("generateContent"))
    .map((m: { name: string }) => m.name.replace(/^models\//, ""));
  const voto = (n: string) => parseFloat((n.match(/gemini-(\d+(\.\d+)?)/) ?? [])[1] ?? "0") * 10
    - (/lite/.test(n) ? 3 : 0) - (/preview|exp/.test(n) ? 1 : 0) - (/latest/.test(n) ? 0.5 : 0);
  const nome = lista.sort((a, b) => voto(b) - voto(a))[0] ?? null;
  if (nome) modelloScelto = { nome, quando: Date.now() };
  return nome;
}

const normale = (s: string) => " " + s.toLowerCase().replace(/[’‘`´]/g, "'").replace(/[^\p{L}\p{N}' ]+/gu, " ").replace(/\s+/g, " ").trim() + " ";
async function termini(testo: string, da: string): Promise<[string, string][]> {
  const f = await tsv();
  if (!f) return [];
  const righe = (da === "it" ? f.itEn : f.enIt).split("\n").map((l) => l.split("\t") as [string, string]).filter((x) => x.length === 2);
  const t = normale(testo);
  return righe.filter(([s]) => s.length > 2 && t.includes(normale(s))).slice(0, 30);
}

function istruzioni(da: string, voci: [string, string][]) {
  const [l1, l2] = da === "it" ? ["italiano", "inglese"] : ["inglese", "italiano"];
  return [
    "Sei un traduttore professionista di inglese tecnico marittimo (Maritime English, IMO SMCP, COLREG, SOLAS).",
    `Traduci il testo dall'${l1} all'${l2}.`,
    "Usa sempre la terminologia nautica professionale usata a bordo e negli esami, mai la traduzione generica o letterale: il gergo nautico va reso con il termine tecnico equivalente.",
    "Quando esiste una frase standard IMO SMCP, usa quella.",
    voci.length ? "Termini del frasario dell'utente da rispettare:\n" + voci.map(([s, t]) => `- ${s} = ${t}`).join("\n") : "",
    "Rispondi solo con la traduzione, senza spiegazioni.",
  ].filter(Boolean).join("\n");
}

async function gemini(testo: string, da: string): Promise<{ ok: true; testo: string; modello: string } | { ok: false; stato: number; messaggio: string }> {
  const m = await modello();
  if (!m) return { ok: false, stato: 502, messaggio: "Gemini non risponde: riprova." };
  const corpo = JSON.stringify({
    systemInstruction: { parts: [{ text: istruzioni(da, await termini(testo, da)) }] },
    contents: [{ role: "user", parts: [{ text: testo }] }],
    generationConfig: { temperature: 0.2, maxOutputTokens: 4096 },
  });
  const r = await fetch(`${GEM}/models/${m}:generateContent`, {
    method: "POST", headers: { "x-goog-api-key": gkey(), "Content-Type": "application/json" }, body: corpo,
  });
  if (r.status === 429) return { ok: false, stato: 429, messaggio: "Limite gratuito di Gemini raggiunto: riprova tra un minuto." };
  if (r.status === 404) modelloScelto = null;                       // modello ritirato: alla prossima richiesta se ne sceglie un altro
  if (!r.ok) { console.error("gemini", m, r.status, await r.text()); return { ok: false, stato: 502, messaggio: "Gemini non risponde: riprova." }; }
  const j = await r.json();
  const parti: { text?: string; thought?: boolean }[] = j.candidates?.[0]?.content?.parts ?? [];
  const out = parti.filter((p) => !p.thought).map((p) => p.text ?? "").join("").trim();
  if (!out) { console.error("gemini vuoto", m, JSON.stringify(j).slice(0, 500)); return { ok: false, stato: 502, messaggio: "Gemini non ha dato una traduzione: riprova." }; }
  return { ok: true, testo: out, modello: m };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(req) });
  const url = new URL(req.url);

  if (req.method === "GET" && url.searchParams.has("stato")) {
    const g = gkey() ? { chiave: true, modello: await modello() } : { chiave: false };
    if (!chiave()) return json(req, { chiave: false, gemini: g });
    const u = await dl("/v2/usage");
    const uso = u.ok ? await u.json() : null;
    const gl = await glossario();
    return json(req, { chiave: u.ok, piano: chiave().endsWith(":fx") ? "free" : "pro", uso, glossario: !!gl, gemini: g });
  }
  if (req.method !== "POST") return json(req, { errore: "metodo" }, 405);

  let corpo: { testo?: string; da?: string; motore?: string; controllo?: boolean };
  try { corpo = await req.json(); } catch { return json(req, { errore: "formato" }, 400); }

  const ut = await utente(req);
  if (corpo.controllo) return json(req, { gemini: !!ut?.gemini, pronto: !!gkey() });
  const conGemini = corpo.motore === "gemini";
  const nome = conGemini ? "Gemini" : "DeepL";
  if (!ut) return json(req, { errore: "accesso", messaggio: `Per la traduzione ${nome} serve l'accesso con il tuo account.` }, 401);
  if (conGemini && !ut.gemini) return json(req, { errore: "gemini", messaggio: "Gemini non è attivo per questo account." }, 403);
  if (conGemini ? !gkey() : !chiave()) return json(req, { errore: "chiave", messaggio: `${nome} non è ancora configurato.` }, 503);
  if (troppe(ut.id)) return json(req, { errore: "limite", messaggio: "Troppe richieste: riprova tra qualche minuto." }, 429);

  const testo = (corpo.testo ?? "").trim();
  const da = corpo.da === "en" ? "en" : "it";
  if (!testo) return json(req, { errore: "vuoto" }, 400);
  if (testo.length > MAX_CARATTERI) return json(req, { errore: "lungo", messaggio: `Massimo ${MAX_CARATTERI} caratteri.` }, 400);

  if (conGemini) {
    const g = await gemini(testo, da);
    if (!g.ok) return json(req, { errore: "gemini", messaggio: g.messaggio }, g.stato);
    return json(req, { traduzione: g.testo, da, a: da === "en" ? "it" : "en", motore: "gemini", modello: g.modello });
  }

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
