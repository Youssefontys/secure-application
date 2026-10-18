"use strict";

// Decoration on the login and registration pages: the figure follows the mouse and reacts to a click.
// A file of its own and no inline script, so the CSP (MIT-21) works without 'unsafe-inline'.
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

  // The mouse position as 0..1 in CSS variables; CSS does the movement itself.
  if (!reduced) {
    window.addEventListener("pointermove", (event) => {
      root.style.setProperty("--mx", (event.clientX / window.innerWidth).toFixed(3));
      root.style.setProperty("--my", (event.clientY / window.innerHeight).toFixed(3));
    }, { passive: true });
  }

  // A click outside the input fields: the figure looks up and the line at the bottom changes.
  document.addEventListener("click", (event) => {
    if (event.target.closest("input, textarea, button, a, label, select")) return;
    document.body.classList.add("alerted");
    window.clearTimeout(timer);
    timer = window.setTimeout(() => document.body.classList.remove("alerted"), 1400);
    if (ticker) ticker.textContent = lines[index++ % lines.length];
    if (reduced) return;
    // A short pulse where the click was; the position through the CSSOM, not a style attribute (CSP).
    const ripple = document.createElement("span");
    ripple.className = "ripple";
    ripple.style.setProperty("--x", `${event.clientX}px`);
    ripple.style.setProperty("--y", `${event.clientY}px`);
    document.body.appendChild(ripple);
    ripple.addEventListener("animationend", () => ripple.remove());
  });
}
