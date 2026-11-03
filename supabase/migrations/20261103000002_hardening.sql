-- JARVIS Edition Studio -- hardening (applies after 20261103000001_schema.sql).
-- 1) Trigger functions must not be callable by API roles (defence in depth).
-- 2) Un-reviewing a chapter must re-open an approved book.

revoke execute on function public.guard_book_approval() from authenticated;
revoke execute on function public.invalidate_book_approval() from authenticated;
revoke execute on function public.invalidate_quality_approval() from authenticated;
revoke execute on function public.invalidate_related_approval() from authenticated;

create function public.reopen_on_unreview()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if old.review_status = 'reviewed' and new.review_status <> 'reviewed' then
    update public.books set status = 'in_review', updated_at = now()
      where id = new.book_id and owner_id = new.owner_id and status = 'approved';
    delete from public.approvals where book_id = new.book_id and owner_id = new.owner_id;
  end if;
  return new;
end;
$$;
revoke execute on function public.reopen_on_unreview() from public, anon, authenticated;
create trigger trg_reopen_on_unreview after update of review_status on public.chapters
  for each row execute function public.reopen_on_unreview();
