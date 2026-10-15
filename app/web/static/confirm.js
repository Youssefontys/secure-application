"use strict";

// Formulieren met data-confirm vragen eerst om bevestiging, zoals bij
// verwijderen. Dit is gebruiksgemak en geen beveiliging: een formulier dat
// van buiten wordt verstuurd, komt nooit langs dit script.
document.addEventListener("submit", (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});
