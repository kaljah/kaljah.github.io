// Keyboard activation for non-button elements that act as buttons (cards, toggles, dropzones).
// Only reacts when the element itself has focus, so nested buttons keep their own behavior.
export const activateOnKey = (e) => {
  if (e.target !== e.currentTarget) return;
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    e.currentTarget.click();
  }
};
