// Tema (S37-05): aplica a preferência deste navegador antes da primeira pintura, para a página não
// piscar. É um arquivo, e não um script na página, porque a CSP só aceita scripts da própria origem.
// A preferência fica em localStorage, chave "ipc:tema": "light", "dark" ou "system" (padrão).
(function () {
  var saved = null;
  try {
    saved = window.localStorage.getItem("ipc:tema");
  } catch (error) {
    saved = null;
  }
  var system = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  document.documentElement.dataset.theme = saved === "light" || saved === "dark" ? saved : system;
})();
