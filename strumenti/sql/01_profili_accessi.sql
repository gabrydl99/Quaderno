-- Quaderno Patentino: foto profilo, registro degli accessi, ruoli super-admin / admin (27/10/2026, versione 1.0)
-- Le tabelle non si leggono direttamente dall'app: solo attraverso le funzioni qui sotto, che controllano il ruolo.

-- ruolo dell'utente collegato, letto ogni volta dal database (un cambio di ruolo vale subito)
create or replace function public.mio_ruolo()
returns text language sql stable security definer set search_path = '' as $$
  select coalesce((select raw_app_meta_data ->> 'ruolo' from auth.users where id = auth.uid()), '');
$$;

create table if not exists public.profili (
  id uuid primary key references auth.users(id) on delete cascade,
  foto text check (foto is null or (char_length(foto) <= 60000 and foto like 'data:image/%')),
  ultimo_segnale timestamptz,
  creato timestamptz not null default now()
);
alter table public.profili enable row level security;

create table if not exists public.accessi (
  id bigint generated always as identity primary key,
  utente uuid not null references auth.users(id) on delete cascade,
  inizio timestamptz not null default now(),
  fine timestamptz not null default now(),
  ip text,
  modello text,
  sistema text,
  browser text
);
create index if not exists accessi_utente_fine on public.accessi (utente, fine desc);
create index if not exists accessi_fine on public.accessi (fine desc);
alter table public.accessi enable row level security;

revoke all on public.profili, public.accessi from anon, authenticated;

-- segnale dall'app (all'apertura e ogni minuto mentre è aperta): "in linea", ultimo accesso, IP e dispositivo.
-- Un accesso = stessa rete e stesso dispositivo senza pause di più di 30 minuti.
create or replace function public.segnale(d jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  u uuid := auth.uid();
  h jsonb := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::jsonb;
  ip text := left(trim(split_part(coalesce(h ->> 'cf-connecting-ip', h ->> 'x-forwarded-for', h ->> 'x-real-ip', ''), ',', 1)), 64);
  mo text := left(coalesce(d ->> 'modello', ''), 60);
  si text := left(coalesce(d ->> 'sistema', ''), 40);
  br text := left(coalesce(d ->> 'browser', ''), 40);
  ul public.accessi;
  pr public.profili;
begin
  if u is null then raise exception 'Accesso richiesto'; end if;
  insert into public.profili (id, ultimo_segnale) values (u, now())
    on conflict (id) do update set ultimo_segnale = now()
    returning * into pr;
  select * into ul from public.accessi where utente = u order by fine desc limit 1;
  if ul.id is not null and ul.fine > now() - interval '30 minutes'
     and coalesce(ul.ip, '') = ip and coalesce(ul.modello, '') = mo and coalesce(ul.sistema, '') = si and coalesce(ul.browser, '') = br then
    update public.accessi set fine = now() where id = ul.id;
  else
    insert into public.accessi (utente, ip, modello, sistema, browser) values (u, nullif(ip, ''), mo, si, br);
  end if;
  return jsonb_build_object('ruolo', public.mio_ruolo())
    || case when coalesce(d ->> 'foto', '') = '1' then jsonb_build_object('foto', pr.foto) else '{}'::jsonb end;
end $$;

-- foto profilo (piccola, già ridotta dal telefono); null = togli la foto
create or replace function public.salva_foto(foto text)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then raise exception 'Accesso richiesto'; end if;
  insert into public.profili (id, foto) values (auth.uid(), foto)
    on conflict (id) do update set foto = excluded.foto;
end $$;

-- elenco degli utenti: il super-admin vede tutto, l'admin solo nome e foto
create or replace function public.elenco_utenti()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare r text := public.mio_ruolo();
begin
  if r = 'superadmin' then
    return coalesce((select jsonb_agg(x order by x.ord, x.nome) from (
      select u.id, coalesce(u.raw_user_meta_data ->> 'nome', split_part(u.email, '@', 1)) as nome,
        coalesce(u.raw_app_meta_data ->> 'ruolo', '') as ruolo,
        case u.raw_app_meta_data ->> 'ruolo' when 'superadmin' then 0 when 'admin' then 1 else 2 end as ord,
        p.foto, u.created_at as registrato,
        greatest(p.ultimo_segnale, u.last_sign_in_at) as ultimo_accesso,
        coalesce(p.ultimo_segnale > now() - interval '150 seconds', false) as in_linea,
        (select count(*) from public.progressi g where g.utente = u.id) as letti,
        (select count(*) from public.accessi a where a.utente = u.id) as n_accessi,
        (select jsonb_build_object('ip', a.ip, 'modello', a.modello, 'sistema', a.sistema, 'browser', a.browser, 'inizio', a.inizio, 'fine', a.fine)
           from public.accessi a where a.utente = u.id order by a.fine desc limit 1) as ultimo
      from auth.users u left join public.profili p on p.id = u.id) x), '[]'::jsonb);
  elsif r = 'admin' then
    return coalesce((select jsonb_agg(x order by lower(x.nome)) from (
      select coalesce(u.raw_user_meta_data ->> 'nome', split_part(u.email, '@', 1)) as nome, p.foto
      from auth.users u left join public.profili p on p.id = u.id) x), '[]'::jsonb);
  end if;
  raise exception 'Riservato agli amministratori';
end $$;

-- registro degli accessi (solo super-admin): di un utente o di tutti
create or replace function public.registro_accessi(chi uuid default null, quanti int default 100)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  if public.mio_ruolo() <> 'superadmin' then raise exception 'Riservato al super-admin'; end if;
  return coalesce((select jsonb_agg(x order by x.fine desc) from (
    select a.utente, coalesce(u.raw_user_meta_data ->> 'nome', split_part(u.email, '@', 1)) as nome,
      a.inizio, a.fine, a.ip, a.modello, a.sistema, a.browser
    from public.accessi a join auth.users u on u.id = a.utente
    where chi is null or a.utente = chi
    order by a.fine desc limit least(greatest(quanti, 1), 500)) x), '[]'::jsonb);
end $$;

-- il super-admin elimina un account (con tutti i suoi dati); non il proprio né un altro super-admin
create or replace function public.elimina_utente(chi uuid)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if public.mio_ruolo() <> 'superadmin' then raise exception 'Riservato al super-admin'; end if;
  if chi = auth.uid() then raise exception 'Non puoi eliminare il tuo account da qui'; end if;
  if (select raw_app_meta_data ->> 'ruolo' from auth.users where id = chi) = 'superadmin' then raise exception 'Un super-admin non si elimina'; end if;
  delete from auth.users where id = chi;
end $$;

-- il super-admin nomina o toglie un admin
create or replace function public.imposta_ruolo(chi uuid, ruolo text)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if public.mio_ruolo() <> 'superadmin' then raise exception 'Riservato al super-admin'; end if;
  if ruolo not in ('admin', '') then raise exception 'Ruolo non valido'; end if;
  if chi = auth.uid() or (select raw_app_meta_data ->> 'ruolo' from auth.users where id = chi) = 'superadmin' then raise exception 'Ruolo del super-admin non modificabile'; end if;
  update auth.users set raw_app_meta_data = case when ruolo = '' then raw_app_meta_data - 'ruolo'
    else raw_app_meta_data || jsonb_build_object('ruolo', ruolo) end where id = chi;
end $$;

-- pulizia automatica (ogni notte): accessi più vecchi di 6 mesi, account non usati da 12 mesi (mai il super-admin)
create or replace function public.pulizia()
returns void language plpgsql security definer set search_path = '' as $$
begin
  delete from public.accessi where fine < now() - interval '6 months';
  delete from auth.users u
  where coalesce(u.raw_app_meta_data ->> 'ruolo', '') <> 'superadmin'
    and coalesce((select p.ultimo_segnale from public.profili p where p.id = u.id), u.last_sign_in_at, u.created_at)
        < now() - interval '12 months'
    and coalesce(u.last_sign_in_at, u.created_at) < now() - interval '12 months';
end $$;

revoke execute on function public.mio_ruolo(), public.segnale(jsonb), public.salva_foto(text), public.elenco_utenti(),
  public.registro_accessi(uuid, int), public.elimina_utente(uuid), public.imposta_ruolo(uuid, text), public.pulizia() from public, anon;
grant execute on function public.mio_ruolo(), public.segnale(jsonb), public.salva_foto(text), public.elenco_utenti(),
  public.registro_accessi(uuid, int), public.elimina_utente(uuid), public.imposta_ruolo(uuid, text) to authenticated;
revoke execute on function public.pulizia() from authenticated;
