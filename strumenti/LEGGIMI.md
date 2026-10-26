# Come si aggiorna il Quaderno (per le prossime sessioni)

Sito: https://gabrydl99.github.io/Quaderno/ — audio divisi tra questo repository (`audio/`) e `gabrydl99/Quaderno-Audio`.

## Costruire l'app
Sorgente dei contenuti: l'HTML dell'artefatto "Quaderno Patentino" (v34). Il contenuto non si modifica qui: solo grafica e funzioni.

```
python3 strumenti/costruisci_pwa.py SORGENTE.html --versione vNN --sfondo --feedback
```
- `--anteprima` (con `--uscita prova.html`): nessun collegamento a Supabase, tutto resta sul telefono.
- Ogni pubblicazione: aumentare la versione (aggiorna anche `sw.js`).

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
Tabelle `segnalazioni` (chiunque invia, legge solo il ruolo admin) e `progressi` (ognuno solo i suoi).
Funzione `elimina_account()`. Admin = `app_metadata.ruolo = 'admin'` (account Gabrydl).
Accesso con nome utente: l'app usa `nome@gabrydl99.github.io` come indirizzo (nessuna email inviata).

## Frasario e Traduttore SMCP (pagina `frasario/`)
Frasi IMO SMCP (Ris. A.918(22), dal PDF "frasi inglesi") con traduzione italiana, glossario nautico IT ⇄ EN, traduttore.
- Dati: `frasario/dati.json`, generato da `strumenti/frasario/` (non modificarlo a mano):
  ```
  python3 strumenti/frasario/build_dati.py frasario/dati.json
  ```
  Scrive anche `frasario/deepl_en_it.tsv` e `deepl_it_en.tsv` (glossario per DeepL).
  Traduzioni delle frasi: `it_*.txt` (riga `numero|testo`); tabelle ordini timone/macchina: `tavole.json`;
  sezione GENERAL: `generale.py`; glossario SMCP: `glos_smcp_it.py`; altri termini: `glos_extra.txt` (`x` = non usare in DeepL).
- Riconoscimento del testo da foto: Tesseract.js 7 in `frasario/ocr/` (inglese + italiano, ~7 MB scaricati solo al primo uso, cache `qp-ocr` nel service worker).
- DeepL: funzione Supabase `traduci` (sorgente `strumenti/frasario/funzione-traduci.ts`), segreto `DEEPL_KEY`.
  Solo utenti con accesso, max 300 caratteri, 30 richieste ogni 10 minuti. Un solo glossario DeepL multilingue (API v3, il piano Free ne accetta pochi). Legge i TSV del sito:
  se cambiano, crea da sola il nuovo glossario su DeepL. Controllo: GET `.../functions/v1/traduci?stato=1`.
- Gemini (traduzione tecnica AI): stessa funzione `traduci`, POST con `motore: "gemini"`, segreto `GEMINI_KEY` (facoltativo `GEMINI_MODEL`,
  altrimenti sceglie da sola il miglior modello "flash"). Passa a Gemini i termini dei TSV presenti nella frase.
  Solo per gli account con `app_metadata.ruolo = 'admin'` o `app_metadata.gemini = true` (la registrazione è libera, quindi non si apre da sola
  ai nuovi account; condizioni Google: servizi a pagamento per utenti UE, niente minorenni). Abilitare un account:
  `update auth.users set raw_app_meta_data = raw_app_meta_data || '{"gemini": true}' where email = 'nome@gabrydl99.github.io';`
  La pagina chiede `{controllo: true}` all'avvio e mostra il riquadro Gemini solo se l'account è abilitato.
- Pagina iniziale: bolla e riquadro in `strumenti/home-aggiunte.html` (inclusi da `costruisci_pwa.py`).
