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

// Een foutmelding krijgt de focus, zodat een schermlezer hem meteen voorleest (tabindex="-1" in base.html).
document.querySelector(".error")?.focus();

// Herstelcode (MIT-11): kopiëren, downloaden, en Verder pas na het vinkje. Zonder JavaScript blijven
// de code en Verder over, en dat werkt dan gewoon.
const recoveryCode = document.getElementById("recovery-code");
if (recoveryCode) {
  const code = recoveryCode.textContent.trim();
  const status = document.getElementById("recovery-status");
  const saved = document.getElementById("recovery-saved");
  const done = document.getElementById("recovery-done");
  for (const element of document.querySelectorAll("[data-js]")) element.hidden = false;
  const update = () => done.setAttribute("aria-disabled", String(!saved.checked));
  saved.addEventListener("change", update);
  done.addEventListener("click", (event) => { if (!saved.checked) event.preventDefault(); });
  update();
  document.getElementById("recovery-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(code);
      status.textContent = "Gekopieerd. Plak hem in je wachtwoordmanager.";
    } catch {
      status.textContent = "Kopiëren lukt hier niet; selecteer de code en kopieer hem zelf.";
    }
  });
  document.getElementById("recovery-download").addEventListener("click", () => {
    const text = `Herstelcode voor Notities\n\n${code}\n\nWerkt één keer. Bewaar hem apart van je telefoon.\n`;
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    link.download = "notities-herstelcode.txt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    status.textContent = "Gedownload. Bewaar het bestand apart van je telefoon.";
  });
}
