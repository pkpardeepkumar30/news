const state = { data: null, archiveIndex: { months: [] }, category: 'All', source: 'all', query: '', view: 'latest', sort: 'latest' };
const el = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const formatDate = value => new Intl.DateTimeFormat('en-IN',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value));
const shortDate = value => new Intl.DateTimeFormat('en-IN',{day:'numeric',month:'short'}).format(new Date(value));
const headlineClass = title => title.length > 90 ? 'headline-long' : title.length > 58 ? 'headline-medium' : '';
const storyPagePath = story => `/stories/${String(story.id ?? '').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,160)}.html`;
const storyLink = (story, label) => `<a class="story-title-link" href="${storyPagePath(story)}">${escapeHtml(label)}</a>`;

async function loadData(){
  try {
    const response = await fetch('data/news.json', {cache:'no-store'});
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    try {
      const archiveResponse = await fetch('data/archive/index.json', {cache:'no-store'});
      if(archiveResponse.ok) state.archiveIndex = await archiveResponse.json();
    } catch (_) {
      state.archiveIndex = { months: [] };
    }
    renderAll();
  } catch(error){
    document.querySelector('main').innerHTML = `<div class="empty-state"><h2>Unable to load news data</h2><p>Run this site through a local web server. Example: <code>python -m http.server 8080</code></p><p>${escapeHtml(error.message)}</p></div>`;
  }
}
function renderAll(){
  const stories = state.data.stories || [];
  el('demoBanner').hidden = !stories.some(s=>s.demo);
  document.querySelector('main').setAttribute('aria-busy','false');
  el('lastBuild').textContent = `Data build: ${formatDate(state.data.generated_at)}`;
  renderStats(stories); renderFilters(); renderLatest(); renderArchive(); renderSources(); bindControls();
}
function renderStats(stories){
  const sourceCount = new Set(stories.flatMap(s=>s.sources.map(source=>source.name))).size;
  const categoryCount = new Set(stories.map(s=>s.category)).size;
  const sourceLinked = stories.length ? Math.round(stories.filter(s=>s.sources.some(source=>source.url)).length/stories.length*100) : 0;
  el('mastheadStats').innerHTML = [
    [stories.length,'current stories'], [sourceCount,'source desks'], [categoryCount,'coverage beats'], [sourceLinked+'%','source-linked']
  ].map(([n,l])=>`<div class="stat"><strong>${n}</strong><span>${l}</span></div>`).join('');
}
function renderFilters(){
  const categories = ['All', ...state.data.categories];
  el('categoryFilters').innerHTML = categories.map(c=>`<button class="filter-chip ${state.category===c?'active':''}" data-category="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join('');
  el('archiveCategory').innerHTML = `<option value="all">All categories</option>` + state.data.categories.map(c=>`<option>${escapeHtml(c)}</option>`).join('');
  document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{state.category=b.dataset.category;renderFilters();renderLatest();}));
}
function filteredStories(){
  const q = state.query.trim().toLowerCase();
  const rows = [...state.data.stories].filter(s=>{
    const categoryOk = state.category==='All' || s.category===state.category;
    const sourceOk = state.source==='all' || s.sources.some(x=>x.type===state.source);
    const haystack = [s.title,s.summary,s.location,s.category,...s.sources.map(x=>x.name)].join(' ').toLowerCase();
    return categoryOk && sourceOk && (!q || haystack.includes(q));
  });
  return rows.sort((a,b)=>state.sort==='underreported' ? b.underreported_score-a.underreported_score : new Date(b.updated_at)-new Date(a.updated_at));
}
function badges(story){
  const sourceTypes = new Set(story.sources.map(s=>s.type));
  const coverageBadge = story.coverage?.status === 'widely_covered' ? '<span class="badge widely-covered">Widely covered</span>' : '';
  return `<div class="image-badges">${story.demo?'<span class="badge demo">Demo</span>':''}${coverageBadge}${sourceTypes.has('social')?'<span class="badge social">Social source</span>':''}${sourceTypes.has('government')?'<span class="badge official">Official source</span>':''}<span class="badge">${escapeHtml(story.evidence_status)}</span></div>`;
}
function image(story){ return `<div class="story-image"><img src="${escapeHtml(story.image.url)}" alt="${escapeHtml(story.image.alt)}" loading="lazy" onerror="this.src='assets/images/fallback.svg'">${badges(story)}</div>`; }
function meta(story){ return `<div class="story-meta"><span>${escapeHtml(story.location)}</span><span>•</span><span>${shortDate(story.updated_at)}</span><span>•</span><span class="confidence ${story.confidence.level.toLowerCase()}">${story.confidence.level} confidence</span></div>`; }
function renderLatest(){
  const stories=filteredStories(); el('resultCount').textContent=`${stories.length} ${stories.length===1?'story':'stories'}`;
  if(!stories.length){ el('leadLayout').innerHTML='<div class="empty-state">No stories match the current filters.</div>'; el('categorySections').innerHTML=''; return; }
  const lead=stories[0], side=stories.slice(1,5);
  el('leadLayout').innerHTML = `<article class="lead-card" data-story="${escapeHtml(lead.id)}">${image(lead)}<div class="lead-copy"><span class="kicker">${escapeHtml(lead.category)} · Underreported ${lead.underreported_score}/100</span><h3 class="${headlineClass(lead.title)}">${storyLink(lead,lead.title)}</h3><p class="story-summary">${escapeHtml(lead.summary)}</p>${meta(lead)}</div></article><aside class="side-list"><div class="side-list-header"><strong>Latest developments</strong><span>${side.length}</span></div>${side.map(s=>`<article class="side-story" data-story="${escapeHtml(s.id)}"><img src="${escapeHtml(s.image.url)}" alt="" loading="lazy" onerror="this.src='assets/images/fallback.svg'"><div><span class="kicker">${escapeHtml(s.category)}</span><h4>${storyLink(s,s.title)}</h4><p>${escapeHtml(s.location)} · ${shortDate(s.updated_at)}</p></div></article>`).join('')}</aside>`;
  const groups = state.data.categories.map(category=>({category,stories:stories.filter(s=>s.category===category)})).filter(g=>g.stories.length);
  el('categorySections').innerHTML = groups.map(g=>`<section class="category-block"><div class="category-header"><h3>${escapeHtml(g.category)}</h3><span>${g.stories.length} ${g.stories.length===1?'story':'stories'}</span></div><div class="news-grid">${g.stories.slice(0,8).map(storyCard).join('')}</div></section>`).join('');
  bindStoryClicks();
}
function storyCard(s){ return `<article class="news-card" data-story="${escapeHtml(s.id)}">${image(s)}<div class="news-copy"><span class="kicker">${escapeHtml(s.location)}</span><h3>${storyLink(s,s.title)}</h3><p class="story-summary">${escapeHtml(s.summary)}</p><div class="card-footer"><span>${escapeHtml(s.sources[0]?.name||'Source pending')}</span><span class="confidence ${s.confidence.level.toLowerCase()}">${s.confidence.level}</span></div></div></article>`; }
function bindStoryClicks(){ document.querySelectorAll('[data-story]').forEach(node=>node.addEventListener('click',event=>{if(event.target.closest('a'))return;openStory(node.dataset.story);})); }
function openStory(id){
  const s=state.data.stories.find(x=>x.id===id); if(!s)return;
  el('storyDialogContent').innerHTML = `<img class="dialog-story-image" src="${escapeHtml(s.image.url)}" alt="${escapeHtml(s.image.alt)}" onerror="this.src='assets/images/fallback.svg'"><div class="dialog-story-body"><div class="dialog-header"><div><p class="eyebrow">${escapeHtml(s.category)} · ${escapeHtml(s.location)}</p><h2 class="${headlineClass(s.title)}">${escapeHtml(s.title)}</h2></div><button class="close-button" onclick="document.getElementById('storyDialog').close()" aria-label="Close">×</button></div><p class="story-summary">${escapeHtml(s.summary)}</p><div class="dialog-columns"><div><h4>Why it matters</h4><p>${escapeHtml(s.why_it_matters)}</p><h4>Evidence assessment</h4><p><strong>${escapeHtml(s.evidence_status)} · ${escapeHtml(s.confidence.level)} confidence (${s.confidence.score}/100)</strong></p><p>${escapeHtml(s.confidence.rationale)}</p>${s.coverage?`<h4>Coverage assessment</h4><p><strong>${escapeHtml(s.coverage.status.replaceAll('_',' '))}</strong> across ${s.coverage.source_count} ${s.coverage.source_count===1?'source desk':'source desks'}.</p><p>${escapeHtml(s.coverage.rationale)}</p>`:''}${s.disagreements?.length?`<h4>Disagreements or gaps</h4><ul>${s.disagreements.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>`:''}</div><aside><a class="permanent-story-link" href="${storyPagePath(s)}">Open permanent story page</a><h4>Original sources</h4>${s.sources.map(x=>`<a class="source-link" href="${escapeHtml(x.url)}" target="_blank" rel="noopener"><strong>${escapeHtml(x.name)}</strong><br><small>${escapeHtml(x.type)} · ${escapeHtml(x.role)}</small></a>`).join('')}<h4>Story details</h4><p>Updated: ${formatDate(s.updated_at)}<br>Underreported score: ${s.underreported_score}/100</p></aside></div></div>`;
  el('storyDialog').showModal();
}
function groupBy(items,keyFn){ return items.reduce((acc,item)=>{const key=keyFn(item);(acc[key] ||= []).push(item);return acc;},{}); }
function renderArchive(){
  const activeMonths = state.data.stories.map(s=>s.published_at.slice(0,7));
  const archivedMonths = (state.archiveIndex.months || []).map(entry=>entry.month);
  const months=[...new Set([...activeMonths,...archivedMonths])].sort().reverse();
  el('archiveMonth').innerHTML=months.map(m=>`<option value="${m}">${new Intl.DateTimeFormat('en-IN',{month:'long',year:'numeric'}).format(new Date(m+'-01'))}</option>`).join('');
  const update=async()=>{
    const month=el('archiveMonth').value, cat=el('archiveCategory').value;
    let rows=state.data.stories.filter(s=>s.published_at.startsWith(month));
    const entry=(state.archiveIndex.months||[]).find(item=>item.month===month);
    if(entry){
      try{
        const response=await fetch(entry.path,{cache:'no-store'});
        if(response.ok){
          const payload=await response.json();
          const byId=new Map(rows.map(story=>[story.id,story]));
          (payload.stories||[]).forEach(story=>byId.set(story.id,story));
          rows=[...byId.values()];
        }
      }catch(_){ /* Keep active stories visible if an archive file is unavailable. */ }
    }
    if(cat!=='all') rows=rows.filter(s=>s.category===cat);
    const days=groupBy(rows,s=>s.published_at.slice(0,10));
    el('archiveResults').innerHTML=Object.entries(days).sort((a,b)=>b[0].localeCompare(a[0])).map(([day,items])=>`<section class="archive-day"><h3>${new Intl.DateTimeFormat('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric'}).format(new Date(day))}</h3>${items.map(s=>`<article class="archive-item" data-story="${escapeHtml(s.id)}"><img src="${escapeHtml(s.image.url)}" alt=""><div><h4>${storyLink(s,s.title)}</h4><p>${escapeHtml(s.category)} · ${escapeHtml(s.location)} · ${escapeHtml(s.evidence_status)}</p></div><span class="confidence ${s.confidence.level.toLowerCase()}">${s.confidence.level}</span></article>`).join('')}</section>`).join('')||'<div class="empty-state">No stories in this archive selection.</div>';
    document.querySelectorAll('.archive-item').forEach(node=>node.addEventListener('click',()=>openArchiveStory(node.dataset.story,rows)));
  };
  el('archiveMonth').onchange=update; el('archiveCategory').onchange=update;
  if(months.length) update(); else el('archiveResults').innerHTML='<div class="empty-state">The archive is empty.</div>';
}
function openArchiveStory(id, rows){
  const existing=state.data.stories.find(story=>story.id===id);
  const archived=rows.find(story=>story.id===id);
  if(!existing && archived) state.data.stories.push(archived);
  openStory(id);
}
function renderSources(){
  const rows=state.data.source_registry||[];
  el('sourceRegistry').innerHTML=`<table class="source-table"><thead><tr><th>Source</th><th>Type</th><th>Ownership / affiliation</th><th>Default treatment</th></tr></thead><tbody>${rows.map(s=>`<tr><td><strong>${escapeHtml(s.name)}</strong></td><td>${escapeHtml(s.type)}</td><td>${escapeHtml(s.ownership)}</td><td>${escapeHtml(s.treatment)}</td></tr>`).join('')}</tbody></table>`;
}
function bindControls(){
  el('searchInput').addEventListener('input',e=>{state.query=e.target.value;renderLatest();});
  el('sourceFilter').addEventListener('change',e=>{state.source=e.target.value;renderLatest();});
  document.querySelectorAll('[data-view]').forEach(btn=>btn.addEventListener('click',()=>setView(btn.dataset.view)));
  el('themeButton').onclick=()=>{document.body.classList.toggle('dark');localStorage.setItem('nazar-theme',document.body.classList.contains('dark')?'dark':'light');};
  if(localStorage.getItem('nazar-theme')==='dark')document.body.classList.add('dark');
  el('submitLeadButton').onclick=()=>el('leadDialog').showModal();
  el('leadForm').addEventListener('submit',saveLead); el('exportLeadsButton').onclick=exportLeads;
}
function setView(view){
  state.sort = view==='underreported' ? 'underreported' : 'latest';
  state.view=view==='underreported'?'latest':view;
  if(view==='underreported'){state.category='All';state.source='all';state.query='';renderFilters();renderLatest();}
  const target=state.view+'View';
  document.querySelectorAll('.view').forEach(v=>{const active=v.id===target;v.classList.toggle('active-view',active);v.hidden=!active;}); document.querySelectorAll('.nav-link').forEach(b=>b.classList.toggle('active',b.dataset.view===view)); window.scrollTo({top:0});
}
function saveLead(e){
  e.preventDefault(); const fd=new FormData(e.target); const leads=JSON.parse(localStorage.getItem('nazar-leads')||'[]'); const observedAt=new Date().toISOString(); leads.push({id:crypto.randomUUID(),url:fd.get('url'),category:fd.get('category'),note:fd.get('note'),platform:fd.get('platform'),metrics:{views:Number(fd.get('views')||0),likes:Number(fd.get('likes')||0),comments:Number(fd.get('comments')||0),shares:Number(fd.get('shares')||0)},submitted_by:fd.get('submittedBy')||'Anonymous',submitted_at:observedAt,observed_at:observedAt}); localStorage.setItem('nazar-leads',JSON.stringify(leads)); e.target.reset(); el('leadDialog').close(); toast('Lead saved locally');
}
function exportLeads(){
  const leads=localStorage.getItem('nazar-leads')||'[]'; const blob=new Blob([leads],{type:'application/json'}); const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='social_submissions.json';a.click();URL.revokeObjectURL(a.href);toast('Lead file exported');
}
function toast(message){el('toast').textContent=message;el('toast').classList.add('show');setTimeout(()=>el('toast').classList.remove('show'),1800);}
loadData();
