-- Quaderno Patentino 1.0: Gabrydl diventa super-admin; segnalazioni solo al super-admin; pulizia automatica ogni notte.
-- (da applicare insieme alla pubblicazione della 1.0: la versione vecchia dell'app controllava ruolo = 'admin')

update auth.users set raw_app_meta_data = raw_app_meta_data || '{"ruolo":"superadmin"}'
where email = 'gabrydl@gabrydl99.github.io';

drop policy if exists "admin legge" on public.segnalazioni;
drop policy if exists "admin segna" on public.segnalazioni;
drop policy if exists "admin elimina" on public.segnalazioni;
create policy "superadmin legge" on public.segnalazioni for select to authenticated using ((select public.mio_ruolo()) = 'superadmin');
create policy "superadmin segna" on public.segnalazioni for update to authenticated
  using ((select public.mio_ruolo()) = 'superadmin') with check ((select public.mio_ruolo()) = 'superadmin');
create policy "superadmin elimina" on public.segnalazioni for delete to authenticated using ((select public.mio_ruolo()) = 'superadmin');

-- eliminare il proprio account dall'app: tutti tranne il super-admin
create or replace function public.elimina_account()
returns void language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then raise exception 'Accesso richiesto'; end if;
  if public.mio_ruolo() = 'superadmin' then raise exception 'L''account super-admin non si elimina dall''app'; end if;
  delete from auth.users where id = auth.uid();
end $$;

-- ogni notte alle 03:17 (ora del server): accessi > 6 mesi, account inattivi > 12 mesi
create extension if not exists pg_cron with schema pg_catalog;
select cron.schedule('quaderno-pulizia', '17 3 * * *', 'select public.pulizia()');
