# Come si aggiorna il Quaderno (per le prossime sessioni)

Sito: https://gabrydl99.github.io/Quaderno/ — audio divisi tra questo repository (`audio/`) e `gabrydl99/Quaderno-Audio`.

## Costruire l'app
Sorgente dei contenuti: l'HTML dell'artefatto "Quaderno Patentino" (v34). Il contenuto non si modifica qui: solo grafica e funzioni.

```
python3 strumenti/costruisci_pwa.py SORGENTE.html --versione 1.01.00 --sfondo --feedback
```
- `--anteprima` (con `--uscita prova.html`): nessun collegamento a Supabase, tutto resta sul telefono.
- Ogni pubblicazione: aumentare la versione (aggiorna anche `sw.js`). Il riquadro "Novità" della 1.01.00 è stato tolto nella 1.01.01 su richiesta.
- **Versioni dalla 1.01.00 (06/11/2026): `1.MM.PP` a due cifre.** La vecchia 1.6 (messaggi) = **1.00.00**.
  - **Media** (`1.01.00`, `1.02.00` …): grafica, disegni, nuovi argomenti, nuove sezioni. Quando sale, la piccola torna a `00`.
  - **Piccola** (`1.01.01`, `1.01.02` …): piccole funzioni, pulsanti, correzioni di errori o di testo.
  - `2.00.00` solo per una svolta vera. Prima: v1…v47, poi 1.0…1.6.
  Versione e data stanno **in fondo alla pagina iniziale** (`<p class="ver-fondo">`).
- Modifiche solo a grafica/funzioni (file di `strumenti/`) senza ricostruire dal sorgente:
  ```
  python3 strumenti/aggiorna_index.py --versione 1.01.01
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

**Dalla 1.1 niente Guest**: senza account l'app mostra solo la schermata d'accesso (Entra / Registrati, in
`account.html`); il contenuto resta nascosto da `html:not(.qp-ok)` in `tema.css`, e lo script `PORTA` in testa
alla pagina mette `qp-ok` se c'è una sessione salvata. Frasario ed Esercizi senza sessione tornano a `../`.
È una schermata d'accesso, non una cifratura: gli appunti restano nel codice della pagina e su GitHub.
Per registrarsi serve il **codice d'accesso** (`impostazioni.codice_registrazione`, maiuscole indifferenti):
lo controlla il trigger `controlla_codice_registrazione` su `auth.users` (l'app lo manda in `data.codice`,
non resta salvato). Admin e super-admin lo vedono e lo cambiano nell'area admin (`codice_accesso()`,
`cambia_codice(nuovo)`). Codice sbagliato → Supabase risponde "Database error saving new user".

Ruoli (`app_metadata.ruolo`, letto dal database con `mio_ruolo()`: un cambio vale subito):
- `superadmin` (Gabrydl, giallo racing): elenco utenti con ultimo accesso, "in linea", registro di IP e dispositivo,
  segnalazioni, può eliminare account e nominare/togliere admin. Non si elimina dall'app.
- `admin`: vede solo nome e foto degli utenti registrati (niente IP, dispositivi, accessi, segnalazioni).

**Messaggi e annunci (1.6)**: scheda "Messaggi" dell'area admin. Admin e super-admin scrivono al singolo utente
(anche toccando il nome nella griglia o "Scrivi" nei dettagli); solo il super-admin manda annunci a tutti.
Il messaggio arriva con `segnale()` e compare in primo piano (`avvisi` in `account.html`) finché non si preme OK;
chi l'ha inviato vede "Letto …" / "Letto da N su M" e può ritirarlo. SQL: `sql/05_messaggi.sql`.
**1.01.00**: annunci anche **anonimi** (casella "Annuncio anonimo", solo super-admin e solo per gli annunci a tutti:
colonna `messaggi.anonimo`; `segnale()` non manda nome, ruolo e foto del mittente). **Allegati nelle segnalazioni**: fino a 3
file da 10 MB (foto rimpicciolite a 1920 px JPEG sul telefono), nel bucket privato `allegati` di Supabase Storage, cartella =
id di chi invia; la segnalazione ne tiene l'elenco in `segnalazioni.allegati` (trigger `controlla_allegati`). Li apre solo il
super-admin con un link firmato di 10 minuti; eliminando la segnalazione si cancellano anche i file. Servono internet (niente coda).
**Pallino rosso** `.qp-n` (in `tema.css`) con le segnalazioni da leggere: sul profilo in alto, su "Area super-admin", sul tasto Apri
del profilo e sulla scheda Segnalazioni. Schede dell'area admin più strette (si leggono tutte e quattro anche a 360 px).
SQL: `sql/06_allegati_annunci_anonimi.sql`.
Nota: dalla 1.5 `account.html` e `feedback.html` erano rimasti indietro rispetto a `index.html`: alla 1.6 sono stati
riallineati estraendoli da `index.html`.

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
SQL in `strumenti/sql/` (01 tabelle e funzioni; 02 super-admin, regole delle segnalazioni, pulizia; 03 codice d'accesso, segnalazioni solo dagli account;
04 nome mostrato = nome utente con cui si entra, `nome_utente(meta, email)`: `user_metadata.nome` vale solo se coincide, maiuscole a parte).
Dalla 1.4: segnalazioni in attesa in una coda per account (`qp-coda-ID` sul telefono); "letto" inviato un passo alla volta;
`costruisci_pwa.py` e `aggiorna_index.py` rendono unici gli id ripetuti nei disegni (`ids_unici`).
Funzione `traduci`: dopo ogni modifica di `strumenti/frasario/funzione-traduci.ts` va ripubblicata su Supabase.

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
