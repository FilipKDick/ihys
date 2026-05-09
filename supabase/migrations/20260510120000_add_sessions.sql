create table if not exists public.sessions (
    token text primary key,
    user_id bigint not null references public.users(id) on delete cascade,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null
);

create index if not exists sessions_user_id_idx on public.sessions(user_id);
