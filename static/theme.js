/* Apply before styles paint to avoid a flash of the wrong theme. */
(() => {
  const key = 'education-insights-theme';
  const root = document.documentElement;
  let selected = 'dark';
  try { selected = localStorage.getItem(key) === 'light' ? 'light' : 'dark'; } catch (_) {}
  function apply(theme) {
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.textContent = theme === 'dark' ? '☀ מצב בהיר' : '☾ מצב כהה';
      button.setAttribute('aria-label', theme === 'dark' ? 'מעבר למצב בהיר' : 'מעבר למצב כהה');
      button.setAttribute('aria-pressed', String(theme === 'dark'));
    });
  }
  apply(selected);
  document.addEventListener('DOMContentLoaded', () => {
    apply(root.dataset.theme);
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.addEventListener('click', () => {
        const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
        apply(next);
        try { localStorage.setItem(key, next); } catch (_) {}
      });
    });
  });
  window.addEventListener('storage', event => {
    if (event.key === key) apply(event.newValue === 'light' ? 'light' : 'dark');
  });
})();
