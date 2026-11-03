-- RLS + editorial-gate tests. Run after stub + migrations. Everything is rolled back.
\set ON_ERROR_STOP on
begin;
insert into auth.users(id,email) values
 ('aaaaaaaa-0000-0000-0000-000000000001','a@test.invalid'),
 ('bbbbbbbb-0000-0000-0000-000000000002','b@test.invalid');

create function public.t_fails(q text) returns void language plpgsql as $$
begin
  begin execute q; exception when others then return; end;
  raise exception 'EXPECTED FAILURE BUT SUCCEEDED: %', q;
end $$;
create function public.t_eq(label text, got text, want text) returns void language plpgsql as $$
begin
  if got is distinct from want then raise exception 'ASSERT % : got % want %', label, got, want; end if;
end $$;
grant execute on function public.t_fails(text), public.t_eq(text,text,text) to authenticated, anon;

-- ===== user A builds a book =====
set local role authenticated;
select set_config('request.jwt.claim.sub','aaaaaaaa-0000-0000-0000-000000000001',true);
insert into public.collections(name) values ('Collection A');
insert into public.books(title) values ('Livre A');
insert into public.chapters(book_id,position,title,content)
  select id,1,'Chapitre 1','Texte fictif.' from public.books where title='Livre A';

-- premature approval is refused (no review, no checks, no sign-off)
select public.t_fails($q$update public.books set status='approved' where title='Livre A'$q$);
-- inserting directly as approved is refused
select public.t_fails($q$insert into public.books(title,status) values ('Direct','approved')$q$);

update public.chapters set review_status='reviewed';
select public.t_fails($q$update public.books set status='approved' where title='Livre A'$q$); -- still no checks
insert into public.quality_checks(book_id,code,verdict)
  select b.id,c,'pass' from public.books b, unnest(array['facts','language','originality','copyright','layout','pricing']) c where b.title='Livre A';
select public.t_fails($q$update public.books set status='approved' where title='Livre A'$q$); -- only 6/7
insert into public.quality_checks(book_id,code,verdict) select id,'human_review','pass' from public.books where title='Livre A';
select public.t_fails($q$update public.books set status='approved' where title='Livre A'$q$); -- no sign-off
insert into public.approvals(book_id,decision) select id,'approved' from public.books where title='Livre A';
update public.books set status='approved' where title='Livre A';
select public.t_eq('approved ok',(select status from public.books where title='Livre A'),'approved');

-- ===== modification of manuscript invalidates =====
update public.chapters set content='Texte modifié.';
select public.t_eq('status after edit',(select status from public.books where title='Livre A'),'in_review');
select public.t_eq('checks reset',(select count(*) from public.quality_checks where verdict='pass')::text,'0');
select public.t_eq('approvals deleted',(select count(*) from public.approvals)::text,'0');

-- re-approve, then un-review a chapter reopens the book
update public.chapters set review_status='reviewed';
insert into public.quality_checks(book_id,code,verdict) values ((select id from public.books where title='Livre A'),'facts','pass')
  on conflict (book_id,code) do update set verdict='pass';
update public.quality_checks set verdict='pass';
insert into public.approvals(book_id,decision) select id,'approved' from public.books where title='Livre A';
update public.books set status='approved' where title='Livre A';
update public.chapters set review_status='draft';
select public.t_eq('unreview reopens',(select status from public.books where title='Livre A'),'in_review');

-- source / cost invalidation
update public.chapters set review_status='reviewed';
update public.quality_checks set verdict='pass';
insert into public.approvals(book_id,decision) select id,'approved' from public.books where title='Livre A';
update public.books set status='approved' where title='Livre A';
insert into public.sources(book_id,title) select id,'Source' from public.books where title='Livre A';
select public.t_eq('source reopens',(select status from public.books where title='Livre A'),'in_review');
select public.t_eq('facts pending',(select verdict from public.quality_checks where code='facts'),'pending');
select public.t_eq('layout untouched',(select verdict from public.quality_checks where code='layout'),'pass');
update public.quality_checks set verdict='pass' where code in ('facts','copyright');
insert into public.approvals(book_id,decision) select id,'approved' from public.books where title='Livre A';
update public.books set status='approved' where title='Livre A';
insert into public.costs(book_id,label,amount_cents) select id,'Impression',1000 from public.books where title='Livre A';
select public.t_eq('cost reopens',(select status from public.books where title='Livre A'),'in_review');
select public.t_eq('pricing pending',(select verdict from public.quality_checks where code='pricing'),'pending');

-- ===== user B sees / touches nothing of A =====
select set_config('t.abook',(select id::text from public.books where title='Livre A'),true);
reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub','bbbbbbbb-0000-0000-0000-000000000002',true);
select public.t_eq('B books',(select count(*) from public.books)::text,'0');
select public.t_eq('B chapters',(select count(*) from public.chapters)::text,'0');
select public.t_eq('B sources',(select count(*) from public.sources)::text,'0');
select public.t_eq('B costs',(select count(*) from public.costs)::text,'0');
select public.t_eq('B checks',(select count(*) from public.quality_checks)::text,'0');
select public.t_eq('B collections',(select count(*) from public.collections)::text,'0');
update public.books set title='Pirate';           -- affects 0 rows, no error
delete from public.chapters;                      -- affects 0 rows
select public.t_fails($q$insert into public.chapters(book_id,position,title) values (current_setting('t.abook')::uuid,9,'Intrus')$q$);
select public.t_fails($q$insert into public.books(owner_id,title) values ('aaaaaaaa-0000-0000-0000-000000000001','Usurpé')$q$);
select public.t_fails($q$insert into public.costs(book_id,label,amount_cents) values (current_setting('t.abook')::uuid,'x',1)$q$);
select public.t_fails($q$insert into public.costs(owner_id,book_id,label,amount_cents) values ('aaaaaaaa-0000-0000-0000-000000000001',current_setting('t.abook')::uuid,'x',1)$q$);
reset role;
select public.t_eq('A untouched',(select title from public.books),'Livre A');
select public.t_eq('A chapters kept',(select count(*) from public.chapters)::text,'1');

-- ===== anon has no access =====
set local role anon;
select public.t_fails($q$select * from public.books$q$);
select public.t_fails($q$insert into public.collections(name) values ('anon')$q$);
reset role;

-- ===== trigger functions not callable by API roles =====
set local role authenticated;
select public.t_fails($q$select public.guard_book_approval()$q$);
reset role;

select 'ALL SQL TESTS PASSED' as result;
rollback;
