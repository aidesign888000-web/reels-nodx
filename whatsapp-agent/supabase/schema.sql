-- Pegar completo en Supabase > SQL Editor > Run
create extension if not exists pgcrypto;

create table if not exists contacts (
  id uuid primary key default gen_random_uuid(),
  phone text unique not null,
  name text,
  email text,
  status text not null default 'nuevo' check (status in ('nuevo','interesado','cita_agendada','cliente','descartado')),
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  contact_id uuid references contacts(id) on delete cascade,
  wamid text unique,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz default now()
);
create index if not exists messages_contact_idx on messages(contact_id, created_at desc);

create table if not exists appointments (
  id uuid primary key default gen_random_uuid(),
  contact_id uuid references contacts(id) on delete cascade,
  google_event_id text,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  title text,
  created_at timestamptz default now()
);

-- Solo el service role (servidor) accede; sin políticas = cerrado para el público.
alter table contacts enable row level security;
alter table messages enable row level security;
alter table appointments enable row level security;
