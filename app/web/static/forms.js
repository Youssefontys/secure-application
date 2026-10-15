"use strict";

// Gedrag van formulieren, op één plek. Dit is gebruiksgemak en geen
// beveiliging: de server controleert alles zelf, en een formulier dat van
// buiten wordt verstuurd, komt nooit langs dit script.

// data-confirm: eerst om bevestiging vragen, zoals bij verwijderen.
document.addEventListener("submit", (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});

// data-validate: de verzendknop staat uit zolang een veld niet voldoet aan
// required of maxlength.
for (const form of document.querySelectorAll("form[data-validate]")) {
  const button = form.querySelector('button[type="submit"]');
  const update = () => { button.disabled = !form.checkValidity(); };
  form.addEventListener("input", update);
  update();
}
