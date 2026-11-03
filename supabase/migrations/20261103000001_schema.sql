-- JARVIS Edition Studio v1.0 -- isolated Supabase project ONLY.
-- Apply to a NEW Supabase project. Never execute against ma-papeterie production.
create extension if not exists pgcrypto;

create table public.collections (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null check (char_length(btrim(name)) between 2 and 160),
  description text not null default '',
  created_at timestamptz not null default now(),
  unique (id, owner_id)
);

create table public.books (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  collection_id uuid,
  title text not null check (char_length(btrim(title)) between 2 and 200),
  subtitle text not null default '',
  author_name text not null default 'Papeterie Reine & Fils',
  target_audience text not null default '',
  positioning text not null default '',
  book_type text not null default 'practical' check (book_type in ('practical','educational','fiction','other')),
  status text not null default 'draft' check (status in ('draft','in_review','approved','archived')),
  format_name text not null default 'A5',
  price_cents integer not null default 1290 check (price_cents between 0 and 1000000),
  ai_disclosure text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id),
  foreign key (collection_id, owner_id) references public.collections (id, owner_id)
);

create table public.chapters (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  book_id uuid not null,
  position integer not null check (position between 1 and 10000),
  title text not null check (char_length(btrim(title)) between 2 and 200),
  content text not null default '',
  review_status text not null default 'draft' check (review_status in ('draft','reviewed')),
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (book_id, position),
  unique (id, owner_id),
  foreign key (book_id, owner_id) references public.books(id, owner_id) on delete cascade
);

create table public.chapter_versions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  chapter_id uuid not null,
  title text not null,
  content text not null,
  saved_at timestamptz not null default now(),
  foreign key (chapter_id, owner_id) references public.chapters(id, owner_id) on delete cascade
);

create table public.sources (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  book_id uuid not null,
  title text not null,
  url text not null default '' check (char_length(url) <= 2000),
  note text not null default '',
  verified boolean not null default false,
  created_at timestamptz not null default now(),
  foreign key (book_id, owner_id) references public.books(id, owner_id) on delete cascade
);

create table public.quality_checks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  book_id uuid not null,
  code text not null check (code in ('facts','language','originality','copyright','layout','pricing','human_review')),
  verdict text not null default 'pending' check (verdict in ('pending','pass','fail')),
  note text not null default '',
  checked_at timestamptz,
  unique (book_id, code),
  foreign key (book_id, owner_id) references public.books(id, owner_id) on delete cascade
);

create table public.approvals (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  book_id uuid not null,
  decision text not null check (decision in ('approved','rejected')),
  note text not null default '',
  decided_at timestamptz not null default now(),
  foreign key (book_id, owner_id) references public.books(id, owner_id) on delete cascade
);

create table public.costs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  book_id uuid not null,
  label text not null check (char_length(btrim(label)) between 2 and 160),
  amount_cents integer not null check (amount_cents between 0 and 100000000),
  category text not null default 'other' check (category in ('editing','printing','cover','marketing','distribution','other')),
  created_at timestamptz not null default now(),
  foreign key (book_id, owner_id) references public.books(id, owner_id) on delete cascade
);

-- RLS: authenticated users see/modify ONLY their own content.
do $$ declare t text;
begin
  foreach t in array array['collections','books','chapters','chapter_versions','sources','quality_checks','approvals','costs'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('create policy own_select on public.%I for select to authenticated using (owner_id = (select auth.uid()))', t);
    execute format('create policy own_insert on public.%I for insert to authenticated with check (owner_id = (select auth.uid()))', t);
    execute format('create policy own_update on public.%I for update to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()))', t);
    execute format('create policy own_delete on public.%I for delete to authenticated using (owner_id = (select auth.uid()))', t);
    execute format('revoke all on public.%I from public, anon', t);
    execute format('grant select, insert, update, delete on public.%I to authenticated', t);
  end loop;
end $$;

-- Approval gate is enforced in DB even when the UI is bypassed.
-- No publishing API or automatic third-party distribution is implemented.
create function public.guard_book_approval()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  passed integer;
  chapter_count integer;
begin
  if new.status = 'approved' and (tg_op = 'INSERT' or old.status is distinct from 'approved') then
    select count(*) into chapter_count
      from public.chapters where book_id = new.id and owner_id = new.owner_id
      and length(btrim(content)) > 0 and review_status = 'reviewed';
    if chapter_count = 0 or exists (
      select 1 from public.chapters where book_id = new.id
      and owner_id = new.owner_id and (review_status <> 'reviewed' or length(btrim(content)) = 0)
    ) then
      raise exception 'Approval blocked: every chapter must be filled and reviewed';
    end if;
    select count(*) into passed from public.quality_checks
      where book_id = new.id and owner_id = new.owner_id and verdict = 'pass';
    if passed <> 7 then
      raise exception 'Approval blocked: all 7 editorial checks must pass';
    end if;
    if not exists (
      select 1 from public.approvals where book_id = new.id and owner_id = new.owner_id
      and decision = 'approved' and decided_at > now() - interval '180 days'
    ) then
      raise exception 'Approval blocked: a recent human sign-off is required';
    end if;
  end if;
  new.updated_at := now();
  return new;
end;
$$;
revoke execute on function public.guard_book_approval() from public, anon;
create trigger trg_guard_book_approval before insert or update of status on public.books
  for each row execute function public.guard_book_approval();

-- Any manuscript modification invalidates prior book approval.
create function public.invalidate_book_approval()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  b_id uuid;
  o_id uuid;
begin
  if tg_op = 'UPDATE' and (old.title, old.content) is not distinct from (new.title, new.content) then
    return new;
  end if;
  if tg_op = 'DELETE' then
    b_id := old.book_id; o_id := old.owner_id;
  else
    b_id := new.book_id; o_id := new.owner_id;
  end if;
  update public.books set status = 'in_review', updated_at = now()
    where id = b_id and owner_id = o_id and status = 'approved';
  update public.quality_checks set verdict = 'pending', note = '', checked_at = null
    where book_id = b_id and owner_id = o_id;
  delete from public.approvals where book_id = b_id and owner_id = o_id;
  if tg_op = 'DELETE' then return old; end if;
  return new;
end;
$$;
revoke execute on function public.invalidate_book_approval() from public, anon;
create trigger trg_invalidate_book_approval after insert or update of title, content or delete
 on public.chapters for each row execute function public.invalidate_book_approval();

create function public.invalidate_quality_approval()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' then
    update public.books set status = 'in_review' where id = old.book_id
      and owner_id = old.owner_id and status = 'approved';
    return old;
  end if;
  if tg_op = 'UPDATE' and old.verdict is distinct from new.verdict then
    update public.books set status = 'in_review' where id = new.book_id
      and owner_id = new.owner_id and status = 'approved';
  end if;
  return new;
end;
$$;
revoke execute on function public.invalidate_quality_approval() from public, anon;
create trigger trg_invalidate_quality_approval after update of verdict or delete
 on public.quality_checks for each row execute function public.invalidate_quality_approval();

-- Sources and costs can invalidate the factual/copyright or pricing sign-off.
create function public.invalidate_related_approval()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  b_id uuid;
  o_id uuid;
  check_codes text[];
begin
  if tg_op = 'DELETE' then
    b_id := old.book_id; o_id := old.owner_id;
  else
    b_id := new.book_id; o_id := new.owner_id;
  end if;
  if tg_table_name = 'sources' then
    check_codes := array['facts','copyright'];
  else
    check_codes := array['pricing'];
  end if;
  update public.books set status = 'in_review', updated_at = now()
    where id = b_id and owner_id = o_id and status = 'approved';
  update public.quality_checks set verdict = 'pending', checked_at = null
    where book_id = b_id and owner_id = o_id and code = any(check_codes);
  delete from public.approvals where book_id = b_id and owner_id = o_id;
  if tg_op = 'DELETE' then return old; end if;
  return new;
end;
$$;
revoke execute on function public.invalidate_related_approval() from public, anon;
create trigger trg_source_invalidate after insert or update or delete on public.sources
  for each row execute function public.invalidate_related_approval();
create trigger trg_cost_invalidate after insert or update or delete on public.costs
  for each row execute function public.invalidate_related_approval();

create index idx_books_owner on public.books(owner_id, created_at desc);
create index idx_chapters_book on public.chapters(book_id, position);
create index idx_versions_chapter on public.chapter_versions(chapter_id, saved_at desc);
create index idx_sources_book on public.sources(book_id);
create index idx_checks_book on public.quality_checks(book_id);
create index idx_approvals_book on public.approvals(book_id, decided_at desc);
create index idx_costs_book on public.costs(book_id);
