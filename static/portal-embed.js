/* Reuse the supplied portal's data, charts, filters and spotlight drill-down. */
(() => {
  const origin = location.origin;
  const notify = message => parent.postMessage(message, origin);
  function title() {
    return document.querySelector('.page[data-active="true"] h1')?.textContent.trim() || 'משל״ט';
  }
  const selectionBar = document.createElement('section');
  selectionBar.className = 'portal-selection-bar';
  selectionBar.setAttribute('aria-label', 'בחירות פעילות');
  document.querySelector('body > .shell').before(selectionBar);
  const selectionStatus = document.createElement('span');
  selectionStatus.className = 'selection-sr-only';
  selectionStatus.setAttribute('role', 'status');
  selectionBar.after(selectionStatus);

  function renderSelections() {
    const labels = {area:'שכונה', school:'מוסד', grade:'שכבה'};
    const selected = Object.keys(labels).filter(key => F[key] !== 'all');
    selectionBar.hidden = PAGE === 'home' && !selected.length;
    selectionBar.replaceChildren();
    const heading = document.createElement('div');
    heading.className = 'selection-heading';
    const name = document.createElement('strong');
    name.textContent = 'בחירות פעילות';
    const count = document.createElement('span');
    count.className = 'selection-count';
    count.textContent = String(selected.length);
    heading.append(name, count);
    const scope = document.createElement('div');
    scope.className = 'selection-scope';
    scope.textContent = 'היקף הפיקוח · מחוז חיפה · יסודי';
    if (PAGE === 'dash' && DASH === 'lo') scope.textContent += ` · ${SUBJ[F.subject]}`;
    const chips = document.createElement('div');
    chips.className = 'selection-chips';
    selected.forEach(key => {
      const value = key === 'school' ? SCHOOL[F.school].name : F[key];
      const chip = document.createElement('span');
      chip.className = 'selection-chip';
      const label = document.createElement('span');
      label.className = 'selection-label';
      label.textContent = labels[key];
      const text = document.createElement('b');
      text.textContent = value;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.dataset.removeSelection = key;
      remove.textContent = '×';
      remove.setAttribute('aria-label', `הסרת בחירה: ${labels[key]} ${value}`);
      remove.title = `הסרת ${labels[key]}`;
      chip.append(label, text, remove);
      chips.append(chip);
    });
    if (!selected.length) {
      const empty = document.createElement('span');
      empty.className = 'selection-empty';
      empty.textContent = 'כל בתי הספר · כל השכבות';
      chips.append(empty);
    }
    selectionBar.append(heading, chips);
    if (selected.length) {
      const clear = document.createElement('button');
      clear.type = 'button';
      clear.className = 'selection-clear';
      clear.dataset.clearSelections = 'true';
      clear.textContent = 'ניקוי בחירות';
      clear.title = 'ניקוי בחירות שכונה, מוסד ושכבה';
      selectionBar.append(clear);
    }
    selectionBar.append(scope);
  }
  selectionBar.addEventListener('click', event => {
    const remove = event.target.closest('button[data-remove-selection]');
    const clear = event.target.closest('button[data-clear-selections]');
    if (!remove && !clear) return;
    const label = remove?.getAttribute('aria-label');
    setFilters(remove ? {[remove.dataset.removeSelection]:'all'} : {area:'all',school:'all',grade:'all'});
    selectionStatus.textContent = clear ? 'כל הבחירות נוקו' : label;
    const next = selectionBar.querySelector('button') || document.querySelector('.page[data-active="true"] select:not(:disabled)');
    next?.focus({preventScroll:true});
  });
  const originalQbar = renderQbar;
  renderQbar = function() { originalQbar(); renderSelections(); };
  const originalShow = showPage;
  showPage = function(name) {
    if (name === 'chat') { openChat(); return; }
    originalShow(name);
    if (PAGE === 'stub') {
      const container = document.querySelector('#stub-main');
      const old = container.querySelector('.portal-empty');
      if (old) old.remove();
      const related = spotsOfWorld(STUB.world).filter(spot => !STUB.dash || spot.actions.some(action => action.dash === STUB.dash));
      if (related.length) {
        const section = document.createElement('section');
        section.className = 'portal-empty';
        const heading = document.createElement('h2');
        heading.textContent = 'זרקורים בתחום';
        section.append(heading);
        related.forEach(spot => {
          const article = document.createElement('article');
          const label = document.createElement('h3');
          const text = document.createElement('p');
          const plain = document.createElement('span');
          plain.innerHTML = spot.title;
          label.textContent = plain.textContent;
          text.textContent = spot.why;
          article.append(label, text);
          section.append(article);
        });
        container.append(section);
      } else {
        const empty = document.createElement('p');
        empty.className = 'portal-empty';
        empty.textContent = 'אין נתונים נוספים להצגה בתחום זה.';
        container.append(empty);
      }
    }
    notify({type:'portal-page', page:PAGE, title:title()});
  };
  openChat = function() {
    notify({type:'portal-chat', title:title()});
  };
  // Keep questions in the application conversation instead of a second chat UI.
  askNow = function(question) {
    notify({type:'portal-chat', title:title(), question:String(question || '')});
  };
  sendTyped = function() {
    const question = ta.value.trim();
    ta.value = '';
    notify({type:'portal-chat', title:title(), question});
  };
  start = function(key) {
    const first = SCENARIOS[key]?.turns.find(turn => turn.role === 'user');
    notify({type:'portal-chat', title:title(), question:first?.text || ''});
  };
  addEventListener('message', event => {
    if (event.origin !== origin || event.source !== parent) return;
    if (event.data?.type === 'portal-theme' && ['dark','light'].includes(event.data.theme)) {
      document.documentElement.dataset.theme = event.data.theme;
      document.documentElement.style.colorScheme = event.data.theme;
    }
    if (event.data?.type === 'portal-home') showPage('home');
    if (event.data?.type === 'portal-spots') openInsights('all');
  });
  document.querySelectorAll('#hh-room,#vd-send').forEach(button => { button.disabled = true; });
  const description = document.querySelector('.hh-text p');
  if (description) description.textContent = 'תמונת מצב מרוכזת של עולמות התוכן, הזרקורים ונתוני בתי הספר.';
  renderHome();
  showPage('home');
  notify({type:'portal-ready'});
})();
