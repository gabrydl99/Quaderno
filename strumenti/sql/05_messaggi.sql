-- 1.6 (05/11/2026): messaggi al singolo utente (admin e super-admin) e annunci a tutti (solo super-admin).
-- Il destinatario li riceve con segnale() e li vede in primo piano finché non preme OK (conferma_messaggio).
-- Tabelle senza accesso diretto (RLS senza regole): solo tramite le funzioni qui sotto.
create table public.messaggi (
  id bigint generated always as identity primary key,
  mittente uuid references auth.users(id) on delete set null,
  mittente_nome text not null,
  destinatario uuid references auth.users(id) on delete cascade,   -- null = annuncio a tutti
  testo text not null check (char_length(testo) between 1 and 1000),
  creato timestamptz not null default now()
);
create table public.messaggi_letti (
  messaggio bigint not null references public.messaggi(id) on delete cascade,
  utente uuid not null references auth.users(id) on delete cascade,
  quando timestamptz not null default now(),
  primary key (messaggio, utente)
);
-- Funzioni: invia_messaggio(a uuid, testo), messaggi_inviati() (admin: i suoi; super-admin: tutti),
-- ritira_messaggio(chi), conferma_messaggio(chi); segnale() restituisce anche 'messaggi' (max 10 da confermare);
-- elenco_utenti() per l'admin ora include l'id; pulizia() cancella i messaggi più vecchi di 12 mesi.
-- Testo completo applicato con le migrazioni Supabase "messaggi_e_annunci" e "pulizia_messaggi".
