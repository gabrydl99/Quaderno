-- Quaderno Patentino 1.4 (31/10/2026): il nome mostrato è sempre il nome utente con cui si entra.
-- Prima veniva da user_metadata.nome, che ogni utente può cambiare da solo (poteva farsi vedere come un altro).
-- Le maiuscole scelte alla registrazione restano (es. "Gabrydl" per gabrydl@…).

create or replace function public.nome_utente(meta jsonb, email text)
returns text language sql immutable set search_path = '' as $$
  select case when lower(meta ->> 'nome') = split_part(coalesce(email, ''), '@', 1) then meta ->> 'nome'
              else split_part(coalesce(email, ''), '@', 1) end;
$$;
revoke execute on function public.nome_utente(jsonb, text) from public, anon, authenticated;

create or replace function public.elenco_utenti()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare r text := public.mio_ruolo();
begin
  if r = 'superadmin' then
    return coalesce((select jsonb_agg(x order by x.ord, x.nome) from (
      select u.id, public.nome_utente(u.raw_user_meta_data, u.email) as nome,
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
      select public.nome_utente(u.raw_user_meta_data, u.email) as nome, p.foto
      from auth.users u left join public.profili p on p.id = u.id) x), '[]'::jsonb);
  end if;
  raise exception 'Riservato agli amministratori';
end $$;

create or replace function public.registro_accessi(chi uuid default null, quanti int default 100)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  if public.mio_ruolo() <> 'superadmin' then raise exception 'Riservato al super-admin'; end if;
  return coalesce((select jsonb_agg(x order by x.fine desc) from (
    select a.utente, public.nome_utente(u.raw_user_meta_data, u.email) as nome,
      a.inizio, a.fine, a.ip, a.modello, a.sistema, a.browser
    from public.accessi a join auth.users u on u.id = a.utente
    where chi is null or a.utente = chi
    order by a.fine desc limit least(greatest(quanti, 1), 500)) x), '[]'::jsonb);
end $$;

create or replace function public.codice_accesso()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  if public.mio_ruolo() not in ('admin', 'superadmin') then raise exception 'Riservato agli amministratori'; end if;
  return (select jsonb_build_object('codice', i.valore, 'aggiornato', i.aggiornato,
            'da', (select public.nome_utente(u.raw_user_meta_data, u.email) from auth.users u where u.id = i.da))
          from public.impostazioni i where i.chiave = 'codice_registrazione');
end $$;

-- account registrati prima del controllo del codice: il codice usato era rimasto nei loro dati
update auth.users set raw_user_meta_data = raw_user_meta_data - 'codice' where raw_user_meta_data ? 'codice';
