(() => {
  const frame = document.getElementById('content-portal');
  const home = document.getElementById('portal-home');
  const attendance = document.getElementById('portal-attendance');
  const spots = document.getElementById('portal-spots');
  const origin = location.origin;
  function send(message) { frame.contentWindow?.postMessage(message, origin); }
  function theme() { send({type:'portal-theme',theme:document.documentElement.dataset.theme}); }
  function navigate(view, message) {
    if (document.body.dataset.chat === 'open') document.getElementById('close-chat').click();
    document.body.dataset.view = view;
    [home,attendance,spots].forEach(button => button.removeAttribute('aria-current'));
    (view === 'attendance' ? attendance : message === 'portal-spots' ? spots : home).setAttribute('aria-current','page');
    if (message) send({type:message});
    window.scrollTo(0,0);
  }
  home.addEventListener('click', () => navigate('portal','portal-home'));
  spots.addEventListener('click', () => navigate('portal','portal-spots'));
  attendance.addEventListener('click', () => navigate('attendance'));
  frame.addEventListener('load',theme);
  new MutationObserver(theme).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  addEventListener('message', event => {
    if (event.origin !== origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === 'portal-ready') theme();
    if (event.data?.type === 'portal-page' && document.body.dataset.view === 'portal') {
      [home,attendance,spots].forEach(button => button.removeAttribute('aria-current'));
      if (event.data.page === 'home') home.setAttribute('aria-current','page');
      if (event.data.page === 'insights') spots.setAttribute('aria-current','page');
    }
    if (event.data?.type === 'portal-chat') {
      document.getElementById('open-chat').click();
      if (event.data.question) {
        const question = document.getElementById('question');
        question.value = event.data.question.slice(0,800);
        question.focus();
      }
    }
  });
  document.getElementById('edit-chat-profile').addEventListener('click', () => {
    document.body.dataset.view = 'attendance';
    document.getElementById('profile-form').scrollIntoView({block:'center'});
  });
})();
