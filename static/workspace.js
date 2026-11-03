/* Keep the same conversation and data nodes while changing workspace layout. */
(() => {
  const openButton = document.getElementById('open-chat');
  const dataButton = document.getElementById('toggle-chat-data');
  let previousFocus = openButton;
  let dashboardScroll = 0;

  function showChat({focus = true} = {}) {
    if (document.body.dataset.chat !== 'open') {
      dashboardScroll = window.scrollY;
      previousFocus = document.activeElement;
    }
    document.body.dataset.chat = 'open';
    document.body.dataset.chatData = 'closed';
    openButton.setAttribute('aria-expanded', 'true');
    dataButton.setAttribute('aria-expanded', 'false');
    dataButton.textContent = 'הצגת נתונים';
    if (focus) document.getElementById('question').focus();
    const messages = document.getElementById('messages');
    messages.scrollTop = messages.scrollHeight;
  }

  function closeChat() {
    document.body.dataset.chat = 'closed';
    document.body.dataset.chatData = 'closed';
    openButton.setAttribute('aria-expanded', 'false');
    dataButton.setAttribute('aria-expanded', 'false');
    window.scrollTo(0, dashboardScroll);
    if (previousFocus && previousFocus.isConnected) previousFocus.focus({preventScroll:true});
  }

  openButton.addEventListener('click', () => showChat());
  document.getElementById('close-chat').addEventListener('click', closeChat);
  document.getElementById('edit-chat-profile').addEventListener('click', () => {
    closeChat();
    document.getElementById('profile-form').scrollIntoView({block:'center'});
    document.getElementById('display-name').focus({preventScroll:true});
  });
  document.getElementById('chat-new').addEventListener('click', () => {
    document.getElementById('new-conversation').click();
    showChat();
  });
  document.getElementById('dashboard-chat-form').addEventListener('submit', event => {
    event.preventDefault();
    const input = document.getElementById('dashboard-question');
    const question = input.value.trim();
    if (!question) return;
    showChat();
    input.value = '';
    void sendQuestion(question);
  });
  dataButton.addEventListener('click', () => {
    const showing = document.body.dataset.chatData !== 'open';
    document.body.dataset.chatData = showing ? 'open' : 'closed';
    dataButton.setAttribute('aria-expanded', String(showing));
    dataButton.textContent = showing ? 'חזרה לשיחה' : 'הצגת נתונים';
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.dataset.chat === 'open') closeChat();
  });
})();
