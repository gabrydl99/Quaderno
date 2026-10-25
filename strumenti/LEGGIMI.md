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
