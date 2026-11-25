-- Run this in the Supabase SQL editor only if these tables do not already exist.
-- This initial unauthenticated version is intended for development only.

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  role text not null default 'attendee' check (role in ('attendee', 'organizer'))
);

create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  organizer_id uuid not null references public.users(id) on delete restrict,
  title text not null check (length(trim(title)) > 0),
  capacity integer not null check (capacity > 0),
  status text not null default 'open' check (status in ('open', 'closed', 'cancelled'))
);

create table if not exists public.registrations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  event_id uuid not null references public.events(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint registrations_user_event_key unique (user_id, event_id)
);

-- Index every foreign key and the query paths used by this API.
create index if not exists events_organizer_id_idx on public.events (organizer_id);
create index if not exists registrations_event_id_created_at_idx on public.registrations (event_id, created_at);
create index if not exists registrations_user_id_created_at_idx on public.registrations (user_id, created_at desc);

-- The API calls this function for a single, race-safe registration transaction.
-- It uses SECURITY INVOKER; the Flask server's service-role client supplies DB access.
create or replace function public.create_event_registration(
  p_user_id uuid,
  p_event_id uuid
)
returns public.registrations
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_event public.events%rowtype;
  v_registration public.registrations%rowtype;
begin
  if not exists (select 1 from public.users where id = p_user_id) then
    raise exception 'user_not_found' using errcode = 'P0001';
  end if;

  select * into v_event
  from public.events
  where id = p_event_id
  for update;

  if not found then
    raise exception 'event_not_found' using errcode = 'P0001';
  end if;
  if v_event.status <> 'open' then
    raise exception 'event_not_open' using errcode = 'P0001';
  end if;
  if exists (
    select 1 from public.registrations
    where user_id = p_user_id and event_id = p_event_id
  ) then
    raise exception 'duplicate_registration' using errcode = 'P0001';
  end if;
  if (select count(*) from public.registrations where event_id = p_event_id) >= v_event.capacity then
    raise exception 'event_at_capacity' using errcode = 'P0001';
  end if;

  insert into public.registrations (user_id, event_id)
  values (p_user_id, p_event_id)
  returning * into v_registration;
  return v_registration;
end;
$$;
