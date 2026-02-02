-- Enable UUID generation helpers (recommended)
create extension if not exists pgcrypto;

-- Enum for message roles (safe to rerun)
do $$
begin
  if not exists (select 1 from pg_type where typname = 'chat_role') then
    create type public.chat_role as enum ('user','assistant','system');
  end if;
end$$;

-- Anonymous users (one per device/user_id)
create table if not exists public.users (
  id uuid primary key,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

-- Chat sessions (threads)
create table if not exists public.chat_sessions (
  id uuid primary key, -- session_id
  user_id uuid not null references public.users(id) on delete cascade,
  title text not null default 'New Conversation',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz null
);

create index if not exists chat_sessions_user_updated_idx
  on public.chat_sessions (user_id, updated_at desc)
  where deleted_at is null;

-- Transcript messages
create table if not exists public.chat_messages (
  id uuid primary key,
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  role public.chat_role not null,
  content text not null,
  created_at timestamptz not null default now(),
  meta jsonb not null default '{}'::jsonb
);

create index if not exists chat_messages_session_created_idx
  on public.chat_messages (session_id, created_at asc);

-- Optional citations/sources (add later if/when you store them)
-- create table if not exists public.message_sources (
--   id uuid primary key,
--   message_id uuid not null references public.chat_messages(id) on delete cascade,
--   source_type text not null,
--   source_id text null,
--   title text null,
--   url text null,
--   snippet text null,
--   score double precision null,
--   extra jsonb not null default '{}'::jsonb
-- );
--
-- create index if not exists message_sources_message_id_idx
--   on public.message_sources (message_id);