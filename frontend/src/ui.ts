export const modKey = /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl";
export const reduced = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
export const message = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
