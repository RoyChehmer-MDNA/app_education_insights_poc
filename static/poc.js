'use strict';
let conversationId=localStorage.getItem('attendance-conversation') || crypto.randomUUID();
localStorage.setItem('attendance-conversation',conversationId);
const $ = (id) => document.getElementById(id);
function el(tag, className, text) { const n=document.createElement(tag); if(className)n.className=className; if(text!==undefined)n.textContent=text; return n; }
function pct(x){return `${Number(x).toFixed(1)}%`;}
async function loadDashboard(){
  try{
    const response=await fetch('/api/dashboard',{credentials:'same-origin'});
    if(!response.ok)throw new Error('הנתונים אינם זמינים');
    const d=await response.json();
    $('summary').replaceChildren();
    [['בתי ספר בפיקוח',d.summary.schools],['ממוצע נוכחות',pct(d.summary.average)],['שינוי ממוצע',`${d.summary.decline} נק׳`],['חריגות',d.summary.flagged]].forEach(([name,value])=>{
      const card=el('div','sum');const body=el('div','');body.append(el('div','v',String(value)),el('div','l',name));card.append(body);$('summary').append(card);
    });
    $('rows').replaceChildren();$('bars').replaceChildren();
    d.rows.forEach(r=>{
      const tr=el('tr');[r.school,r.grade,pct(r.previous),pct(r.current),`${(r.current-r.previous).toFixed(1)} נק׳`].forEach(v=>tr.append(el('td','',v)));$('rows').append(tr);
      const line=el('div','poc-br');line.append(el('span','',r.school));const track=el('div','poc-track');
      const prev=el('span','poc-prev');prev.style.width=`${r.previous}%`;
      const curr=el('span','poc-curr');curr.style.width=`${r.current}%`;
      track.append(prev,curr);line.append(track,el('strong','',pct(r.current)));$('bars').append(line);
    });
    $('data-badge').textContent=d.source==='uploaded_csv'?'נתוני CSV':'נתוני נוכחות';
    const selected=$('school-scope').value;
    $('school-scope').replaceChildren(new Option('כל בתי הספר',''));
    d.rows.forEach(r=>$('school-scope').add(new Option(r.school,r.school_id)));
    $('school-scope').value=selected;
  }catch(e){$('data-badge').textContent='שגיאה בטעינת הנתונים';}
}
function addMessage(css,text){const n=el('div',css,text);$('messages').append(n);$('messages').scrollTop=$('messages').scrollHeight;return n;}
async function sendQuestion(q){
  addMessage('poc-user',q);const pending=addMessage('poc-bot','מנתח את הנתונים...');
  try{
    const response=await fetch('/api/chat',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,conversation_id:conversationId,school_id:$('school-scope').value,reset_context:true})});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'שגיאה');
    pending.textContent=data.answer;
    $('messages').scrollTop=$('messages').scrollHeight;
    void loadGaps();
  }catch(e){pending.textContent=`לא ניתן להשלים את הפעולה: ${e.message}`;}
}
$('chat-form').addEventListener('submit',(e)=>{e.preventDefault();const q=$('question').value.trim();if(q){$('question').value='';void sendQuestion(q);}});
$('starter').addEventListener('click',()=>void sendQuestion('איפה יש ירידה חריגה בנוכחות שכבה ד׳ ומה כדאי לעשות?'));
void loadDashboard();

async function api(url,options={}){
  const response=await fetch(url,options);const data=await response.json();
  if(!response.ok)throw new Error(data.error||'שגיאה');return data;
}
async function workspaceAction(action){try{await action();$('workspace-status').textContent='הפעולה הושלמה';}catch(e){$('workspace-status').textContent=e.message;}}
async function loadGaps(){
  const data=await api('/api/gaps');$('gaps').replaceChildren();
  data.gaps.forEach(g=>{const line=el('div','',`מוסד ${g.school} `);const select=el('select');
    [['open','פתוח'],['in_progress','בטיפול'],['resolved','נסגר']].forEach(([v,t])=>select.add(new Option(t,v)));
    select.value=g.status;select.setAttribute('aria-label',`מצב פער ${g.school}`);
    select.addEventListener('change',()=>void workspaceAction(async()=>{await api(`/api/gaps/${g.school}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:select.value})});}));line.append(select);$('gaps').append(line);
  });
}
$('upload-form').addEventListener('submit',e=>{e.preventDefault();void workspaceAction(async()=>{const form=new FormData();form.append('file',$('attendance-file').files[0]);await api('/api/files/attendance',{method:'POST',body:form});await loadDashboard();});});
$('reset-data').addEventListener('click',()=>void workspaceAction(async()=>{await api('/api/files/attendance',{method:'DELETE'});await loadDashboard();}));
function renderProfile(data){
 const profile=data.profile;
 $('display-name').value=profile.display_name||'';
 $('profile-role').value=profile.role||'';
 $('profile-district').value=profile.district||'';
 $('chat-user-details').textContent=[profile.display_name,profile.role,profile.district?`מחוז ${profile.district}`:'',`${data.school_count} בתי ספר`].filter(Boolean).join(' · ');
 const avatar=document.querySelector('.tn-avatar');
 avatar.textContent=profile.display_name.trim().charAt(0)||'מ';
 avatar.setAttribute('aria-label',profile.display_name||'משתמשת');
}
$('profile-form').addEventListener('submit',e=>{e.preventDefault();void workspaceAction(async()=>{
 const data=await api('/api/profile',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:$('display-name').value.trim(),role:$('profile-role').value.trim(),district:$('profile-district').value.trim()})});
 renderProfile(data);
});});
$('new-conversation').addEventListener('click',()=>{conversationId=crypto.randomUUID();localStorage.setItem('attendance-conversation',conversationId);$('messages').replaceChildren();});
void workspaceAction(async()=>{
 renderProfile(await api('/api/profile'));
 const history=await api(`/api/conversations/${conversationId}`);
 history.messages.forEach(m=>{addMessage('poc-user',m.question);addMessage('poc-bot',m.response.answer);});await loadGaps();
});
