import type { ReactNode } from "react";

export function KeyHint({ children }: { children: ReactNode }) {
  return <kbd aria-hidden="true">{children}</kbd>;
}
