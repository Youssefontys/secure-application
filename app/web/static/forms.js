"use strict";

// Form behaviour, in one place. This is convenience, not security: the
// server checks everything itself, and a form sent from elsewhere never
// passes through this script.

// data-confirm: ask for confirmation first, as when deleting.
document.addEventListener("submit", (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});

// data-validate: the submit button stays off while a field does not meet
// required or maxlength.
for (const form of document.querySelectorAll("form[data-validate]")) {
  const button = form.querySelector('button[type="submit"]');
  const update = () => { button.disabled = !form.checkValidity(); };
  form.addEventListener("input", update);
  update();
}

// An error message gets the focus, so a screen reader reads it out at once (tabindex="-1" in base.html).
document.querySelector(".error")?.focus();

// Recovery code (MIT-11): copy, download, and Continue only after the checkbox. Without JavaScript the
// code and Continue remain, and that works just as well.
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
      status.textContent = "Copied. Paste it into your password manager.";
    } catch {
      status.textContent = "Copying does not work here; select the code and copy it yourself.";
    }
  });
  document.getElementById("recovery-download").addEventListener("click", () => {
    const text = `Recovery code for Notes\n\n${code}\n\nWorks once. Keep it separate from your phone.\n`;
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    link.download = "notes-recovery-code.txt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    status.textContent = "Downloaded. Keep the file separate from your phone.";
  });
}
