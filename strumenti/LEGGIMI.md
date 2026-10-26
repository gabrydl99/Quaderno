# Come si aggiorna il Quaderno (per le prossime sessioni)

Sito: https://gabrydl99.github.io/Quaderno/ — audio divisi tra questo repository (`audio/`) e `gabrydl99/Quaderno-Audio`.

## Costruire l'app
Sorgente dei contenuti: l'HTML dell'artefatto "Quaderno Patentino" (v34). Il contenuto non si modifica qui: solo grafica e funzioni.

```
python3 strumenti/costruisci_pwa.py SORGENTE.html --versione 1.1 --sfondo --feedback
```
- `--anteprima` (con `--uscita prova.html`): nessun collegamento a Supabase, tutto resta sul telefono.
- Ogni pubblicazione: aumentare la versione (aggiorna anche `sw.js`).
- **Versioni**: fino al 26/10/2026 erano v1…v47; da lì la v47 è diventata **1.0** e si conta 1.1, 1.2 … (2.0 solo per cambi grossi).
  Versione e data stanno **in fondo alla pagina iniziale** (`<p class="ver-fondo">`), non più in alto.
- Modifiche solo a grafica/funzioni (file di `strumenti/`) senza ricostruire dal sorgente:
  ```
  python3 strumenti/aggiorna_index.py --versione 1.1
  ```
  sostituisce in `index.html` le parti cambiate dall'ultimo commit e aggiorna versione, data e `sw.js`.

## Pagine Esercizi
```
python3 strumenti/costruisci_esercizi.py ASSETTO.html assetto "Assetto e pescaggi"
python3 strumenti/costruisci_esercizi.py CARTEGGIO.html carteggio "Carteggio con carta 5D"
```
Sorgenti: gli artefatti "Assetto e Pescaggi" e "Carteggio con carta 5D". Grafica in `tema-esercizi.css`.

## File
- `tema.css` grafica · `pagina.html` disegni e riquadri della home · `istruzioni.html` "Come si usa"
- `account.html` profilo, argomenti letti, progressi · `feedback.html` segnalazioni e area admin
- `installa.html` tasto Installa · `sfondo.html` immagine della home
- `modifiche.json` parti tolte su richiesta · `mappa_audio.json` audio → file · `supabase.json` progetto e chiave pubblica

## Supabase (progetto cvyuytnouuapmazjnebc)
Accesso con nome utente: l'app usa `nome@gabrydl99.github.io` come indirizzo (nessuna email inviata).

Ruoli (`app_metadata.ruolo`, letto dal database con `mio_ruolo()`: un cambio vale subito):
- `superadmin` (Gabrydl, giallo racing): elenco utenti con ultimo accesso, "in linea", registro di IP e dispositivo,
  segnalazioni, può eliminare account e nominare/togliere admin. Non si elimina dall'app.
- `admin`: vede solo nome e foto degli utenti registrati (niente IP, dispositivi, accessi, segnalazioni).

Tabelle: `segnalazioni` (chiunque invia, legge solo il super-admin), `progressi` (ognuno solo i suoi),
`profili` (foto ~15 KB come data URL, ultimo segnale) e `accessi` (inizio, fine, IP, modello, sistema, browser):
queste due non si leggono direttamente, solo con le funzioni.
Funzioni: `segnale(d)` (l'app la chiama all'apertura e ogni minuto, solo con l'account: "in linea" = segnale
negli ultimi 150 s; un accesso = stessa rete e dispositivo senza pause > 30 min; IP preso dalle intestazioni
della richiesta), `salva_foto`, `elenco_utenti`, `registro_accessi`, `elimina_utente`, `imposta_ruolo`,
`elimina_account` (il proprio account), `pulizia()`.
Pulizia automatica con pg_cron (`quaderno-pulizia`, ogni notte alle 03:17): accessi più vecchi di 6 mesi,
account non usati da 12 mesi (mai il super-admin). Termini di servizio: testo `TERMINI` in `account.html`,
mostrato sotto "Segnalazioni e feedback" e alla registrazione.
SQL in `strumenti/sql/` (01 tabelle e funzioni; 02 super-admin, regole delle segnalazioni, pulizia).

## Frasario e Traduttore SMCP (pagina `frasario/`)
Frasi IMO SMCP (Ris. A.918(22), dal PDF "frasi inglesi") con traduzione italiana, glossario nautico IT ⇄ EN, traduttore Gemini.
- Dati: `frasario/dati.json`, generato da `strumenti/frasario/` (non modificarlo a mano):
  ```
  python3 strumenti/frasario/build_dati.py frasario/dati.json
  ```
  Scrive anche `frasario/deepl_en_it.tsv` e `deepl_it_en.tsv` (termini passati a Gemini).
  Traduzioni delle frasi: `it_*.txt` (riga `numero|testo`); tabelle ordini timone/macchina: `tavole.json`;
  sezione GENERAL: `generale.py`; glossario SMCP: `glos_smcp_it.py`; altri termini: `glos_extra.txt` (`x` = non usare in DeepL).
- Riconoscimento del testo da foto: Tesseract.js 7 in `frasario/ocr/` (inglese + italiano, ~7 MB scaricati solo al primo uso, cache `qp-ocr` nel service worker).
  Due tasti: fotocamera (foto scattata ora, `capture="environment"`) e galleria.
- Glossario: mentre scrivi compaiono fino a 8 suggerimenti (IT ed EN) che iniziano con le lettere scritte;
  toccandone uno il glossario si filtra e la voce lampeggia.
- Traduttore Gemini (DeepL tolto il 26/10/2026): funzione Supabase `traduci` (sorgente `strumenti/frasario/funzione-traduci.ts`), segreto `GEMINI_KEY`
  (facoltativo `GEMINI_MODEL` per fissare il modello; altrimenti prova i "flash" più recenti e, se occupati, i "flash-lite").
  Max 300 caratteri, 30 richieste ogni 10 minuti per utente. Passa a Gemini i termini dei TSV del glossario presenti nella frase
  (`frasario/deepl_*.tsv`: il nome è rimasto, ora servono a Gemini). Controllo: GET `.../functions/v1/traduci?stato=1`.
  Dal 26/10/2026 aperto a tutti gli account registrati (`GEMINI_PER_TUTTI = true` nella funzione; l'utente dirà quando chiuderlo).
  Con `false` vale solo per `app_metadata.ruolo = 'admin'` o `app_metadata.gemini = true` (condizioni Google: servizi a pagamento per
  utenti UE, niente minorenni). I Guest vedono il riquadro con l'invito ad accedere. Abilitare un account:
  `update auth.users set raw_app_meta_data = raw_app_meta_data || '{"gemini": true}' where email = 'nome@gabrydl99.github.io';`
- Pagina iniziale: bolla e riquadro in `strumenti/home-aggiunte.html` (inclusi da `costruisci_pwa.py`).
