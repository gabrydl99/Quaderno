-- 1.01.00 (06/11/2026): allegati nelle segnalazioni e annunci anonimi.

-- Allegati: file nel bucket privato "allegati" (cartella = id di chi invia); nella segnalazione resta l'elenco.
alter table public.segnalazioni add column allegati jsonb not null default '[]'::jsonb;
alter table public.segnalazioni add constraint segnalazioni_allegati_check
  check (jsonb_typeof(allegati) = 'array' and jsonb_array_length(allegati) <= 3);

-- ogni allegato deve stare nella cartella di chi invia (nessuno può "collegare" file altrui)
create or replace function public.controlla_allegati() returns trigger
language plpgsql security definer set search_path = '' as $$
declare e jsonb;
begin
  for e in select * from jsonb_array_elements(new.allegati) loop
    if jsonb_typeof(e) <> 'object' or coalesce(e ->> 'path', '') not like auth.uid()::text || '/%'
       or char_length(coalesce(e ->> 'nome', '')) > 120 then
      raise exception 'Allegato non valido';
    end if;
  end loop;
  return new;
end $$;
create trigger segnalazioni_allegati before insert on public.segnalazioni
  for each row when (new.allegati <> '[]'::jsonb) execute function public.controlla_allegati();

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('allegati', 'allegati', false, 10485760, array[
  'image/jpeg','image/png','image/webp','image/gif','image/heic','image/heif',
  'application/pdf','text/plain',
  'application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-powerpoint','application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'audio/mpeg','audio/mp4','audio/x-m4a','audio/aac','audio/ogg','audio/wav','video/mp4','video/quicktime'])
on conflict (id) do nothing;

create policy "allegati: chi ha l'account carica nella sua cartella" on storage.objects for insert to authenticated
  with check (bucket_id = 'allegati' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "allegati: legge il super-admin" on storage.objects for select to authenticated
  using (bucket_id = 'allegati' and (select public.mio_ruolo()) = 'superadmin');
create policy "allegati: elimina il super-admin" on storage.objects for delete to authenticated
  using (bucket_id = 'allegati' and (select public.mio_ruolo()) = 'superadmin');

-- Annunci anonimi: solo il super-admin, solo per gli annunci a tutti; chi riceve non vede il mittente.
alter table public.messaggi add column anonimo boolean not null default false;
drop function public.invia_messaggio(uuid, text);
create function public.invia_messaggio(a uuid, testo text, anonimo boolean default false)
returns bigint language plpgsql security definer set search_path = '' as $$
declare r text := public.mio_ruolo(); t text := btrim(coalesce(testo, '')); n text; i bigint;
begin
  if r not in ('admin', 'superadmin') then raise exception 'Riservato agli amministratori'; end if;
  if t = '' then raise exception 'Scrivi il messaggio'; end if;
  if char_length(t) > 1000 then raise exception 'Messaggio troppo lungo (massimo 1000 caratteri)'; end if;
  if a is null and r <> 'superadmin' then raise exception 'Gli annunci a tutti li manda solo il super-admin'; end if;
  if anonimo and a is not null then raise exception 'Solo gli annunci a tutti possono essere anonimi'; end if;
  if a is not null and not exists (select 1 from auth.users where id = a) then raise exception 'Utente non trovato'; end if;
  if a = auth.uid() then raise exception 'Non puoi scrivere a te stesso'; end if;
  select public.nome_utente(raw_user_meta_data, email) into n from auth.users where id = auth.uid();
  insert into public.messaggi (mittente, mittente_nome, destinatario, testo, anonimo)
    values (auth.uid(), coalesce(n, 'admin'), a, t, coalesce(anonimo, false)) returning id into i;
  return i;
end $$;
revoke execute on function public.invia_messaggio(uuid, text, boolean) from public, anon;
grant execute on function public.invia_messaggio(uuid, text, boolean) to authenticated;
-- messaggi_inviati(): aggiunto il campo "anonimo"; segnale(): per gli annunci anonimi da, ruolo_da e foto_da vuoti.
-- Testo completo applicato con la migrazione Supabase "allegati_e_annunci_anonimi".
