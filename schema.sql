-- Run this in the Supabase SQL editor only if these tables do not already exist.
-- This initial unauthenticated version is intended for development only.

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  role text not null default 'student' check (role in ('student', 'organizer'))
);

create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  organizer_id uuid not null references public.users(id) on delete restrict,
  title text not null check (length(trim(title)) > 0),
  capacity integer not null default 50 check (capacity > 0),
  status text not null default 'upcoming' check (status in ('upcoming', 'open', 'closed', 'cancelled'))
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
