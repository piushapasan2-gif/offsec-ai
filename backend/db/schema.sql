-- ════════════════════════════════════════════════════════════
--  OffSec AI 2025 — Supabase Schema
--  Run this in Supabase Dashboard → SQL Editor
-- ════════════════════════════════════════════════════════════

-- Enable extensions
create extension if not exists "uuid-ossp";

-- ─── Chat sessions ───
create table if not exists chat_sessions (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references auth.users(id) on delete cascade,
    title text,
    meta jsonb default '{}'::jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
create index if not exists idx_chat_sessions_user on chat_sessions(user_id, created_at desc);

-- ─── Chat messages ───
create table if not exists chat_messages (
    id bigserial primary key,
    session_id uuid references chat_sessions(id) on delete cascade,
    user_id uuid references auth.users(id) on delete cascade,
    role text not null,
    content text not null,
    provider text,
    model text,
    elapsed_ms integer,
    ts timestamptz default now()
);
create index if not exists idx_chat_messages_session on chat_messages(session_id, ts);

-- ─── Audit log ───
create table if not exists audit_log (
    id bigserial primary key,
    user_id uuid references auth.users(id) on delete cascade,
    ts timestamptz default now(),
    event text not null,
    actor text default 'user',
    payload jsonb default '{}'::jsonb
);
create index if not exists idx_audit_user_ts on audit_log(user_id, ts desc);
create index if not exists idx_audit_event on audit_log(event);

-- ─── Findings (pentest results) ───
create table if not exists findings (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references auth.users(id) on delete cascade,
    engagement text,
    severity text check (severity in ('critical','high','medium','low','info')),
    title text not null,
    description text,
    evidence jsonb default '{}'::jsonb,
    cvss numeric,
    cve_ids text[] default '{}',
    mitre_tactics text[] default '{}',
    status text default 'open' check (status in ('open','triaged','fixed','wontfix','duplicate')),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
create index if not exists idx_findings_user on findings(user_id, created_at desc);
create index if not exists idx_findings_severity on findings(severity, status);

-- ─── Engagements (project scopes) ───
create table if not exists engagements (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references auth.users(id) on delete cascade,
    name text not null,
    in_scope text[] default '{}',
    blocklist text[] default '{}',
    notes text,
    created_at timestamptz default now()
);
create index if not exists idx_engagements_user on engagements(user_id);

-- ─── Discovered assets ───
create table if not exists assets (
    id bigserial primary key,
    user_id uuid references auth.users(id) on delete cascade,
    engagement_id uuid references engagements(id) on delete cascade,
    host text not null,
    port integer,
    service text,
    banner text,
    tech jsonb default '{}'::jsonb,
    discovered_at timestamptz default now()
);
create index if not exists idx_assets_engagement on assets(engagement_id);
create index if not exists idx_assets_host on assets(host);

-- ═══════════════════════════════════════════════════════════
--  Row Level Security — each user only sees their own data
-- ═══════════════════════════════════════════════════════════

alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;
alter table audit_log enable row level security;
alter table findings enable row level security;
alter table engagements enable row level security;
alter table assets enable row level security;

-- Generic policy template: user_id must equal auth.uid()
drop policy if exists "own_chat_sessions" on chat_sessions;
create policy "own_chat_sessions" on chat_sessions
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own_chat_messages" on chat_messages;
create policy "own_chat_messages" on chat_messages
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own_audit_log" on audit_log;
create policy "own_audit_log" on audit_log
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own_findings" on findings;
create policy "own_findings" on findings
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own_engagements" on engagements;
create policy "own_engagements" on engagements
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own_assets" on assets;
create policy "own_assets" on assets
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════
--  Helper: trigger to keep updated_at fresh
-- ═══════════════════════════════════════════════════════════
create or replace function set_updated_at() returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists chat_sessions_updated on chat_sessions;
create trigger chat_sessions_updated before update on chat_sessions
    for each row execute function set_updated_at();

drop trigger if exists findings_updated on findings;
create trigger findings_updated before update on findings
    for each row execute function set_updated_at();
