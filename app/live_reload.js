/* Local development only. Retry quietly while the Python server restarts. */
(() => {
  const initial = document.currentScript.dataset.revision;
  const draftKey = 'dev-reload-question';
  const question = document.getElementById('question');
  const draft = sessionStorage.getItem(draftKey);
  if (question && draft !== null) {
    question.value = draft;
    sessionStorage.removeItem(draftKey);
  }
  async function check() {
    try {
      const response = await fetch('/__dev/revision', {cache: 'no-store'});
      if (response.ok && (await response.json()).revision !== initial) {
        if (question) sessionStorage.setItem(draftKey, question.value);
        window.location.reload();
        return;
      }
    } catch (_) { /* The reloader may briefly stop the server. */ }
    window.setTimeout(check, 1000);
  }
  window.setTimeout(check, 1000);
})();
