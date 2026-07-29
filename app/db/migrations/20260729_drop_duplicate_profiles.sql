begin;

-- User identity and nickname now live in Supabase Auth (auth.users metadata).
-- Preserve existing nicknames before removing the duplicate public table.
update auth.users as auth_user
set raw_user_meta_data =
  coalesce(auth_user.raw_user_meta_data, '{}'::jsonb)
  || jsonb_build_object('nickname', profile.nickname)
from public.profiles as profile
where auth_user.id = profile.id
  and nullif(trim(profile.nickname), '') is not null
  and nullif(trim(auth_user.raw_user_meta_data ->> 'nickname'), '') is null;

-- Remove only auth.users triggers whose trigger function references profiles.
-- This prevents future signups from calling an obsolete profile insert function.
do $$
declare
  trigger_record record;
begin
  for trigger_record in
    select trigger_info.tgname
    from pg_trigger as trigger_info
    join pg_proc as trigger_function
      on trigger_function.oid = trigger_info.tgfoid
    where trigger_info.tgrelid = 'auth.users'::regclass
      and not trigger_info.tgisinternal
      and pg_get_functiondef(trigger_function.oid) ilike '%profiles%'
  loop
    execute format(
      'drop trigger %I on auth.users',
      trigger_record.tgname
    );
  end loop;
end
$$;

-- Abort instead of cascading if another public table still references profiles.
do $$
begin
  if exists (
    select 1
    from pg_constraint constraint_info
    join pg_class referenced_table
      on referenced_table.oid = constraint_info.confrelid
    join pg_namespace referenced_schema
      on referenced_schema.oid = referenced_table.relnamespace
    where constraint_info.contype = 'f'
      and referenced_schema.nspname = 'public'
      and referenced_table.relname = 'profiles'
  ) then
    raise exception 'public.profiles still has foreign-key dependants';
  end if;
end
$$;

drop table if exists public.profiles;

commit;
