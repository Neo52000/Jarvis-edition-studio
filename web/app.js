import {h, safeFile, amount} from './util.js';
import {SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY} from './config.js';

const $ = id => document.getElementById(id);
const CHECKS = [
  ['facts','Exactitude des informations'], ['language','Orthographe et lisibilité'],
  ['originality','Originalité et absence de plagiat'], ['copyright','Droits des textes et visuels'],
  ['layout','Mise en page et épreuve'], ['pricing','Prix et coûts vérifiés'],
  ['human_review','Relecture humaine complète']
];
const statusLabel = {draft:'Brouillon',in_review:'En révision',approved:'Approuvé',archived:'Archivé'};
const {createClient} = window.supabase;
let db, user, collections=[], books=[], selected=null, details=null, tab='chapters';

function notice(value, error=false){const el=$('message');el.textContent=value;el.className='message'+(error?' error':'');el.hidden=false;}
function fail(e){notice(e?.message||String(e),true);console.error(e);}
function credentialCheck(){
  if(!SUPABASE_URL.startsWith('https://') || SUPABASE_URL.includes('YOUR_NEW_PROJECT') || !SUPABASE_PUBLISHABLE_KEY.startsWith('sb_publishable_') || SUPABASE_PUBLISHABLE_KEY.includes('REPLACE_ME')) {
    notice('Configure web/config.js avec l’URL et la clé publiable de ton NOUVEAU projet Supabase.',true);
    return false;
  }
  return true;
}
function download(name,obj){const blob=new Blob([JSON.stringify(obj,null,2)],{type:'application/json;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
async function query(table,options={}){let q=db.from(table).select('*');if(options.book_id)q=q.eq('book_id',options.book_id);if(options.owner_id)q=q.eq('owner_id',options.owner_id);if(options.order)q=q.order(options.order);const {data,error}=await q;if(error)throw error;return data;}
async function insert(table,payload){const {data,error}=await db.from(table).insert(payload).select();if(error)throw error;return data;}
async function update(table,id,payload){const {data,error}=await db.from(table).update(payload).eq('id',id).select();if(error)throw error;return data[0];}
async function remove(table,id){const {error}=await db.from(table).delete().eq('id',id);if(error)throw error;}
async function login(){
  const email=$('login-email').value.trim();
  const {error}=await db.auth.signInWithOtp({email,options:{shouldCreateUser:false,emailRedirectTo:location.origin+location.pathname}});
  if(error)throw error;notice('Lien envoyé. Consulte ta boîte mail pour te connecter.');
}
async function load(){
  if(!user)return;
  [collections,books]=await Promise.all([query('collections',{order:'created_at'}),query('books',{order:'created_at'})]);
  $('collection-count').textContent=collections.length;$('book-count').textContent=books.length;
  renderPortfolio();if(selected){selected=books.find(b=>b.id===selected.id)||null;if(selected)await loadDetails();else $('editor').hidden=true;}
}
function renderPortfolio(){
  const current=$('collection-filter').value;
  $('collection-filter').innerHTML='<option value="">Toutes les collections</option>'+collections.map(c=>`<option value="${h(c.id)}">${h(c.name)}</option>`).join('');
  $('collection-filter').value=collections.some(c=>c.id===current)?current:'';
  const filtered=books.filter(b=>!$('collection-filter').value||b.collection_id===$('collection-filter').value);
  $('books').innerHTML=filtered.length?filtered.map(b=>`<button class="book-item ${selected?.id===b.id?'active':''}" data-open="${h(b.id)}"><span><strong>${h(b.title)}</strong><small>${h(collections.find(c=>c.id===b.collection_id)?.name||'Sans collection')} · ${amount(b.price_cents)}</small></span><span class="pill">${h(statusLabel[b.status]||b.status)}</span></button>`).join(''):'<div class="empty">Aucun livre. Créez votre premier projet.</div>';
}
async function loadDetails(){
  if(!selected)return;
  const tables=['chapters','chapter_versions','sources','quality_checks','approvals','costs'];
  const values=await Promise.all(tables.map(t=>t==='chapter_versions'?Promise.resolve([]):query(t,{book_id:selected.id})));
  details=Object.fromEntries(tables.map((t,i)=>[t,values[i]]));
  details.chapters.sort((a,b)=>a.position-b.position);
  const ids=details.chapters.map(c=>c.id);
  if(ids.length){
    const {data,error}=await db.from('chapter_versions').select('*').in('chapter_id',ids).order('saved_at',{ascending:false}).limit(200);
    if(error)throw error;
    details.chapter_versions=data;
  }
  details.approvals.sort((a,b)=>new Date(b.decided_at)-new Date(a.decided_at));
  $('editor').hidden=false;
  $('editor-title').textContent=selected.title;
  $('editor-meta').textContent=`${selected.author_name} · ${selected.format_name} · ${statusLabel[selected.status]||selected.status} · ${amount(selected.price_cents)}`;
  $('tabs').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
  renderTab();renderApproval();renderPortfolio();
}
function renderTab(){
  const target=$('tab-content');if(!details)return;
  if(tab==='chapters'){
    target.innerHTML=`<div class="form-row"><input id="chapter-title" placeholder="Titre du nouveau chapitre"/><button data-action="add-chapter">+ Chapitre</button></div>`+
      (details.chapters.length?details.chapters.map(c=>`<article class="item"><div class="item-head"><h3>${c.position}. ${h(c.title)}</h3><span class="pill">${c.review_status==='reviewed'?'Relu':'Brouillon'}</span></div><div class="editor-label">Contenu Markdown</div><textarea data-chapter-content="${h(c.id)}" aria-label="Contenu de ${h(c.title)}">${h(c.content)}</textarea><div class="form-row"><button data-action="save-chapter" data-id="${h(c.id)}">Enregistrer + version</button><button class="secondary" data-action="toggle-review" data-id="${h(c.id)}">${c.review_status==='reviewed'?'Réouvrir':'Marquer relu'}</button><button class="secondary" data-action="delete-chapter" data-id="${h(c.id)}">Supprimer</button></div><small>Dernière modification : ${new Date(c.updated_at).toLocaleDateString('fr-FR')}</small><details><summary class="muted">Historique des versions (${details.chapter_versions.filter(v=>v.chapter_id===c.id).length})</summary>${details.chapter_versions.filter(v=>v.chapter_id===c.id).map(v=>`<div class="item-head version"><small>${new Date(v.saved_at).toLocaleString('fr-FR')} · ${h(v.title)}</small><button class="secondary" data-action="restore-version" data-id="${h(v.id)}">Restaurer</button></div>`).join('')||'<p class="hint">Aucune ancienne version.</p>'}</details></article>`).join(''):'<div class="empty">Ajoute un chapitre pour commencer le manuscrit.</div>');
  }else if(tab==='sources'){
    target.innerHTML=`<div class="form-row"><input id="source-title" placeholder="Titre de la source"/><input id="source-url" placeholder="https://... (facultatif)"/><button data-action="add-source">+ Source</button></div>`+
      (details.sources.length?details.sources.map(s=>`<article class="item"><div class="item-head"><strong>${h(s.title)}</strong><span class="pill">${s.verified?'Vérifiée':'À vérifier'}</span></div><p>${h(s.url)}</p><div class="form-row"><button class="secondary" data-action="verify-source" data-id="${h(s.id)}">${s.verified?'Annuler vérification':'Confirmer la vérification'}</button><button class="secondary" data-action="delete-source" data-id="${h(s.id)}">Supprimer</button></div></article>`).join(''):'<div class="empty">Aucune source enregistrée.</div>');
  }else if(tab==='quality'){
    target.innerHTML=`<p class="hint">Chaque contrôle exige une vérification humaine. L'IA peut assister, mais ne peut pas s'auto-certifier.</p>`+CHECKS.map(([code,title])=>{
      const q=details.quality_checks.find(x=>x.code===code);return `<article class="item"><div class="item-head"><strong>${h(title)}</strong><span class="pill">${q?.verdict==='pass'?'Validé':q?.verdict==='fail'?'Échec':'En attente'}</span></div><div class="form-row"><button data-action="set-check" data-code="${code}" data-verdict="pass">Validé</button><button class="secondary" data-action="set-check" data-code="${code}" data-verdict="fail">À corriger</button><button class="secondary" data-action="set-check" data-code="${code}" data-verdict="pending">Réinitialiser</button></div>${q?.note?`<small>${h(q.note)}</small>`:''}</article>`;
    }).join('');
  }else if(tab==='costs'){
    const total=details.costs.reduce((a,x)=>a+x.amount_cents,0);
    target.innerHTML=`<p>Coûts saisis : <strong>${amount(total)}</strong>. Prix de vente indicatif : <strong>${amount(selected.price_cents)}</strong>. Ce calcul ne représente pas un bénéfice net.</p>`+
      `<div class="form-row"><input id="cost-label" placeholder="Libellé du coût"/><input id="cost-amount" type="number" min="0" step="0.01" placeholder="Montant €"/><select id="cost-category"><option value="editing">Édition</option><option value="printing">Impression</option><option value="cover">Couverture</option><option value="marketing">Marketing</option><option value="distribution">Distribution</option><option value="other">Autre</option></select><button data-action="add-cost">+ Coût</button></div>`+
      (details.costs.length?details.costs.map(c=>`<div class="item item-head"><span>${h(c.label)} <small>(${h(c.category)})</small></span><span><strong>${amount(c.amount_cents)}</strong> <button class="secondary" data-action="delete-cost" data-id="${h(c.id)}">Retirer</button></span></div>`).join(''):'<div class="empty">Aucun coût saisi.</div>');
  }
}
function renderApproval(){
  const chaptersOk=details.chapters.length>0&&details.chapters.every(c=>c.review_status==='reviewed'&&c.content.trim());
  const checksOk=CHECKS.every(([code])=>details.quality_checks.some(c=>c.code===code&&c.verdict==='pass'));
  const approved=selected.status==='approved';
  $('approval-msg').textContent=approved?'Document approuvé. Toute modification du manuscrit annule ce statut.':`${details.chapters.filter(c=>c.review_status==='reviewed').length}/${details.chapters.length} chapitres relus · ${details.quality_checks.filter(c=>c.verdict==='pass').length}/7 contrôles validés.`;
  $('approve').disabled=approved||!chaptersOk||!checksOk;
  $('approve').textContent=approved?'Déjà approuvé':'Signer et approuver';
}
async function clickAction(btn){
  const action=btn.dataset.action,id=btn.dataset.id;
  if(action==='add-chapter'){
    const title=$('chapter-title').value.trim();if(title.length<2)throw new Error('Titre du chapitre trop court.');
    await insert('chapters',{book_id:selected.id,title,position:Math.max(0,...details.chapters.map(c=>c.position))+1});
  }else if(action==='save-chapter'){
    const c=details.chapters.find(x=>x.id===id);const content=document.querySelector(`textarea[data-chapter-content="${id}"]`).value;
    if(c.content!==content){await insert('chapter_versions',{chapter_id:id,title:c.title,content:c.content});await update('chapters',id,{content,review_status:'draft',updated_at:new Date().toISOString()});}
    else {notice('Aucun changement à enregistrer.');return;}
  }else if(action==='restore-version'){
    const version=details.chapter_versions.find(v=>v.id===id);
    if(!version)throw new Error('Version introuvable.');
    if(!confirm('Restaurer cette version ? La version actuelle sera sauvegardée dans l’historique et la validation réouverte.'))return;
    const chapter=details.chapters.find(c=>c.id===version.chapter_id);
    await insert('chapter_versions',{chapter_id:chapter.id,title:chapter.title,content:chapter.content});
    await update('chapters',chapter.id,{title:version.title,content:version.content,review_status:'draft',updated_at:new Date().toISOString()});
  }else if(action==='toggle-review'){
    const c=details.chapters.find(x=>x.id===id);
    if(c.review_status!=='reviewed'&&!c.content.trim())throw new Error('Enregistre un contenu avant de le valider.');
    await update('chapters',id,{review_status:c.review_status==='reviewed'?'draft':'reviewed',updated_at:new Date().toISOString()});
  }else if(action==='delete-chapter'){
    if(!confirm('Supprimer définitivement ce chapitre et son historique ?'))return;await remove('chapters',id);
  }else if(action==='add-source'){
    const title=$('source-title').value.trim();const url=$('source-url').value.trim();if(title.length<2)throw new Error('Titre de source requis.');
    if(url&&!/^https?:\/\//i.test(url))throw new Error('L’URL doit commencer par http:// ou https://');
    await insert('sources',{book_id:selected.id,title,url});
  }else if(action==='verify-source'){
    const s=details.sources.find(x=>x.id===id);await update('sources',id,{verified:!s.verified});
  }else if(action==='delete-source'){
    if(!confirm('Supprimer cette source ?'))return;await remove('sources',id);
  }else if(action==='set-check'){
    const code=btn.dataset.code,verdict=btn.dataset.verdict;
    const old=details.quality_checks.find(x=>x.code===code);
    const note=verdict==='pending'?'':prompt('Note de vérification (recommandée) :',old?.note||'');
    if(note===null)return;
    const fields={verdict,note,checked_at:verdict==='pending'?null:new Date().toISOString()};
    if(old)await update('quality_checks',old.id,fields);
    else await insert('quality_checks',{book_id:selected.id,code,...fields});
  }else if(action==='add-cost'){
    const label=$('cost-label').value.trim(),val=Number($('cost-amount').value);
    if(label.length<2||!Number.isFinite(val)||val<0||!$('cost-amount').value)throw new Error('Coût invalide.');
    await insert('costs',{book_id:selected.id,label,amount_cents:Math.round(val*100),category:$('cost-category').value});
  }else if(action==='delete-cost'){
    if(!confirm('Supprimer ce coût ?'))return;await remove('costs',id);
  }
  await load();notice('Modifications enregistrées.');
}
async function createBook(){
  const title=prompt('Titre du nouveau livre :','Le français sans fautes au quotidien');if(title===null)return;if(title.trim().length<2)throw new Error('Titre trop court.');
  const collectionId=$('collection-filter').value||null;
  const priceRaw=prompt('Prix public TTC envisagé (€) :','12.90');if(priceRaw===null)return;
  const price=Number(priceRaw.replace(',','.'));if(!Number.isFinite(price)||price<0)throw new Error('Prix invalide.');
  const [book]=await insert('books',{title:title.trim(),collection_id:collectionId,price_cents:Math.round(price*100)});
  selected=book;await load();notice('Livre créé.');
}
async function createCollection(){
  const name=prompt('Nom de la collection :','Guides pratiques');if(name===null)return;if(name.trim().length<2)throw new Error('Nom trop court.');
  await insert('collections',{name:name.trim()});await load();notice('Collection créée.');
}
async function approve(){
  if(!confirm(`Confirmer la validation humaine de « ${selected.title} » ?`))return;
  await insert('approvals',{book_id:selected.id,decision:'approved',note:'Visa explicite depuis le tableau de bord'});
  await update('books',selected.id,{status:'approved'});await load();notice('Livre approuvé (publication externe toujours manuelle).');
}
async function exportSnapshot(){
  const snapshot={schema_version:1,book:selected,collection:collections.find(c=>c.id===selected.collection_id)||null,chapters:details.chapters,sources:details.sources,quality_checks:details.quality_checks,approvals:details.approvals,costs:details.costs,exported_at:new Date().toISOString()};
  download(`${safeFile(selected.title)}.json`,snapshot);notice('Dossier exporté. Utilise scripts/export_book.py pour générer DOCX/PDF/Markdown.');
}
async function wrap(task){try{await task();}catch(e){fail(e);}}

$('login-form').addEventListener('submit',e=>{e.preventDefault();wrap(login);});
$('logout').addEventListener('click',()=>wrap(async()=>{await db.auth.signOut();}));
$('new-book').addEventListener('click',()=>wrap(createBook));
$('new-collection').addEventListener('click',()=>wrap(createCollection));
$('collection-filter').addEventListener('change',renderPortfolio);
$('approve').addEventListener('click',()=>wrap(approve));
$('download-snapshot').addEventListener('click',()=>wrap(exportSnapshot));
$('books').addEventListener('click',e=>wrap(async()=>{const btn=e.target.closest('[data-open]');if(!btn)return;selected=books.find(b=>b.id===btn.dataset.open);await loadDetails();}));
$('tabs').addEventListener('click',e=>{const btn=e.target.closest('[data-tab]');if(btn){tab=btn.dataset.tab;loadDetails().catch(fail);}});
$('tab-content').addEventListener('click',e=>{const btn=e.target.closest('[data-action]');if(btn)wrap(()=>clickAction(btn));});

if(credentialCheck()){
  db=createClient(SUPABASE_URL,SUPABASE_PUBLISHABLE_KEY);
  db.auth.onAuthStateChange((_event,session)=>{setTimeout(()=>wrap(async()=>{
    user=session?.user||null;$('auth-panel').hidden=!!user;$('dashboard').hidden=!user;$('logout').hidden=!user;
    if(user)await load();else{selected=null;details=null;}
  }),0);});
}
