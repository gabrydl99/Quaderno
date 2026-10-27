-- Quaderno Patentino 1.1 (27/10/2026): niente più Guest. Per registrarsi serve il codice d'accesso,
-- che admin e super-admin vedono e cambiano dall'app. Le segnalazioni le inviano solo gli account.

create table if not exists public.impostazioni (
  chiave text primary key,
  valore text not null,
  aggiornato timestamptz not null default now(),
  da uuid references auth.users(id) on delete set null
);
alter table public.impostazioni enable row level security;
revoke all on public.impostazioni from anon, authenticated;
-- il codice vero NON va scritto qui (il repository è pubblico): si imposta a parte, poi si cambia dall'app
insert into public.impostazioni (chiave, valore) values ('codice_registrazione', 'DA-IMPOSTARE')
  on conflict (chiave) do nothing;

-- leggere il codice attuale (admin e super-admin)
create or replace function public.codice_accesso()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  if public.mio_ruolo() not in ('admin', 'superadmin') then raise exception 'Riservato agli amministratori'; end if;
  return (select jsonb_build_object('codice', i.valore, 'aggiornato', i.aggiornato,
            'da', (select coalesce(u.raw_user_meta_data ->> 'nome', split_part(u.email, '@', 1)) from auth.users u where u.id = i.da))
          from public.impostazioni i where i.chiave = 'codice_registrazione');
end $$;

-- cambiarlo (admin e super-admin)
create or replace function public.cambia_codice(nuovo text)
returns void language plpgsql security definer set search_path = '' as $$
declare n text := btrim(coalesce(nuovo, ''));
begin
  if public.mio_ruolo() not in ('admin', 'superadmin') then raise exception 'Riservato agli amministratori'; end if;
  if n !~ '^[A-Za-z0-9._-]{4,30}$' then raise exception 'Il codice deve avere da 4 a 30 caratteri: lettere, numeri, punto, trattino o trattino basso'; end if;
  insert into public.impostazioni (chiave, valore, aggiornato, da) values ('codice_registrazione', n, now(), auth.uid())
    on conflict (chiave) do update set valore = excluded.valore, aggiornato = now(), da = auth.uid();
end $$;

-- controllo alla registrazione: l'app manda il codice nei metadati (data.codice); se è sbagliato l'account non viene creato.
-- Maiuscole/minuscole e spazi ai lati non contano; il codice non resta salvato nell'account.
create or replace function public.controlla_codice_registrazione()
returns trigger language plpgsql security definer set search_path = '' as $$
declare atteso text;
begin
  select valore into atteso from public.impostazioni where chiave = 'codice_registrazione';
  if atteso is null or lower(btrim(coalesce(new.raw_user_meta_data ->> 'codice', ''))) <> lower(atteso) then
    raise exception 'Codice di registrazione non valido';
  end if;
  new.raw_user_meta_data := coalesce(new.raw_user_meta_data, '{}'::jsonb) - 'codice';
  return new;
end $$;
drop trigger if exists controlla_codice_registrazione on auth.users;
create trigger controlla_codice_registrazione before insert on auth.users
  for each row execute function public.controlla_codice_registrazione();

revoke execute on function public.codice_accesso(), public.cambia_codice(text), public.controlla_codice_registrazione() from public, anon;
grant execute on function public.codice_accesso(), public.cambia_codice(text) to authenticated;
revoke execute on function public.controlla_codice_registrazione() from authenticated;
grant execute on function public.controlla_codice_registrazione() to supabase_auth_admin;

-- segnalazioni: solo dagli account (prima anche dai Guest)
drop policy if exists "chiunque invia" on public.segnalazioni;
drop policy if exists "utenti inviano" on public.segnalazioni;
create policy "utenti inviano" on public.segnalazioni for insert to authenticated with check (letto = false);
