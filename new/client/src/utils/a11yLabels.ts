// BUG-107: most forms render `<div className="input-group"><label>X</label><input/></div>` without
// htmlFor / id, so screen readers announce unlabeled fields. This links each such label to the
// first form control in its group, once, for every page (installed from main.jsx).
let seq = 0;
const CONTROLS = "input:not([type=hidden]), select, textarea";

export function linkFormLabels(root: Document | HTMLElement = document): void {
  root.querySelectorAll<HTMLLabelElement>("label:not([for])").forEach((label) => {
    if (label.querySelector(CONTROLS)) return; // wrapping label is already associated
    const group = label.parentElement;
    if (!group) return;
    const control = [...group.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(CONTROLS)].find(
      (c) => !(c as any).labels?.length && !c.getAttribute("aria-label") && !c.getAttribute("aria-labelledby"),
    );
    if (!control) return;
    if (!control.id) control.id = `fld-${++seq}`;
    label.htmlFor = control.id;
  });
}

export function installLabelLinker(root: HTMLElement = document.body): () => void {
  if (typeof MutationObserver === "undefined" || !root) return () => {};
  let queued = false;
  const run = () => {
    queued = false;
    linkFormLabels(root);
  };
  const obs = new MutationObserver(() => {
    if (!queued) {
      queued = true;
      (window.requestAnimationFrame || setTimeout)(run);
    }
  });
  obs.observe(root, { childList: true, subtree: true });
  run();
  return () => obs.disconnect();
}
