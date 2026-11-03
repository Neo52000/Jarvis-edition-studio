// Pure helpers (no DOM, no network) so they can be unit-tested with `node --test`.
export const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const amount = cents => new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format((cents||0)/100);
export function safeFile(v){return String(v).normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^A-Za-z0-9_-]+/g,'-').slice(0,64)||'livre';}
