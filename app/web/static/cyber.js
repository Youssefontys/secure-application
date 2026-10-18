"use strict";

// Decoratie op de inlog- en registratiepagina's: de figuur volgt de muis en reageert op een klik.
// Een eigen bestand en geen inline script, zodat de CSP (MIT-21) zonder 'unsafe-inline' kan.
if (document.querySelector(".scene")) {
  const root = document.documentElement;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const ticker = document.querySelector("[data-ticker]");
  const lines = [
    "attempt registered ~ source: local session",
    "nothing to see here, try the login field",
    "click logged ~ 1 event in the queue",
    "scan refused ~ no open port found",
    "nice try. next time with a valid code",
  ];
  let index = 0;
  let timer = null;

  // De muispositie als 0..1 in CSS-variabelen; de verplaatsing zelf doet CSS.
  if (!reduced) {
    window.addEventListener("pointermove", (event) => {
      root.style.setProperty("--mx", (event.clientX / window.innerWidth).toFixed(3));
      root.style.setProperty("--my", (event.clientY / window.innerHeight).toFixed(3));
    }, { passive: true });
  }

  // Een klik buiten de invoervelden: de figuur kijkt op en de regel onderin verandert.
  document.addEventListener("click", (event) => {
    if (event.target.closest("input, textarea, button, a, label, select")) return;
    document.body.classList.add("alerted");
    window.clearTimeout(timer);
    timer = window.setTimeout(() => document.body.classList.remove("alerted"), 1400);
    if (ticker) ticker.textContent = lines[index++ % lines.length];
    if (reduced) return;
    // Een korte puls op de plek van de klik; de positie via CSSOM en niet via een style-attribuut (CSP).
    const ripple = document.createElement("span");
    ripple.className = "ripple";
    ripple.style.setProperty("--x", `${event.clientX}px`);
    ripple.style.setProperty("--y", `${event.clientY}px`);
    document.body.appendChild(ripple);
    ripple.addEventListener("animationend", () => ripple.remove());
  });
}
