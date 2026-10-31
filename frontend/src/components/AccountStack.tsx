import {
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  type CSSProperties,
  type Ref,
  type RefObject,
} from "react";
import type { Account } from "../api";
import { nextColor } from "../colors";
import { reduced } from "../ui";
import { AccountCard } from "./AccountCard";

export interface AccountStackHandle {
  prepareAddition: (id: number, rect: DOMRect) => void;
  animateRemoval: (id: number) => Promise<void>;
}

interface AccountStackProps {
  ref: Ref<AccountStackHandle>;
  accounts: Account[];
  selectedId: number | null;
  busy: boolean;
  onSelect: (account: Account) => void;
  onAdd: () => void;
  previewRef: RefObject<HTMLDivElement | null>;
}

export function AccountStack({
  ref,
  accounts,
  selectedId,
  busy,
  onSelect,
  onAdd,
  previewRef,
}: AccountStackProps) {
  const root = useRef<HTMLDivElement>(null);
  const addition = useRef<{ id: number; rect: DOMRect } | null>(null);
  useImperativeHandle(
    ref,
    () => ({
      prepareAddition(id, rect) {
        addition.current = { id, rect };
      },
      async animateRemoval(id) {
        const card = root.current?.querySelector<HTMLElement>(
          `[data-account="${id}"]`,
        );
        if (card && !reduced())
          await card.animate(
            [{ opacity: 1 }, { opacity: 0, transform: "translateX(-80px)" }],
            {
              duration: 260,
              easing: "cubic-bezier(.5,0,.75,0)",
              fill: "forwards",
            },
          ).finished;
      },
    }),
    [],
  );
  useLayoutEffect(() => {
    const target = addition.current;
    if (!target) return;
    addition.current = null;
    const card = root.current?.querySelector<HTMLElement>(
      `[data-account="${target.id}"]`,
    );
    if (!card || reduced()) return;
    const to = card.getBoundingClientRect();
    const ghost = card
      .querySelector(".account-card")!
      .cloneNode(true) as HTMLElement;
    const source = previewRef.current?.querySelector(
      ".account-card",
    ) as HTMLElement | null;
    if (source) {
      // Clone the saved card so its name and colour survive the editor reset.
      Object.assign(ghost.style, {
        position: "fixed",
        left: `${target.rect.left}px`,
        top: `${target.rect.top}px`,
        width: `${target.rect.width}px`,
        height: `${target.rect.height}px`,
        zIndex: "60",
        pointerEvents: "none",
        margin: "0",
      });
      ghost.setAttribute("aria-hidden", "true");
      document.body.append(ghost);
      const flight = ghost.animate(
        [
          { transform: "none", transformOrigin: "0 0" },
          {
            transform: `translate(${to.left - target.rect.left}px, ${to.top - target.rect.top}px) scale(${to.width / target.rect.width})`,
            transformOrigin: "0 0",
          },
        ],
        { duration: 560, easing: "cubic-bezier(.3,.7,.2,1)", fill: "forwards" },
      );
      flight.finished.then(
        () => ghost.remove(),
        () => ghost.remove(),
      );
      card.animate([{ opacity: 0 }, { opacity: 1 }], {
        duration: 1,
        delay: 540,
        fill: "backwards",
      });
    }
    previewRef.current?.animate(
      [
        { opacity: 0, transform: "scale(.96)" },
        { opacity: 1, transform: "none" },
      ],
      { duration: 380, delay: 220, fill: "backwards" },
    );
  });
  return (
    <>
      {accounts.length > 0 && (
        <div
          className="account-stack"
          ref={root}
          aria-label="Your accounts"
          style={{ "--count": accounts.length + 1 } as CSSProperties}
        >
          {accounts.map((account) => (
            <button
              type="button"
              key={account.id}
              className={`stack-card ${selectedId === account.id ? "selected" : ""}`}
              data-account={account.id}
              aria-label={`Edit ${account.name}`}
              aria-pressed={selectedId === account.id}
              disabled={busy}
              onClick={() => onSelect(account)}
            >
              <AccountCard name={account.name} color={account.color} />
            </button>
          ))}
          <button
            type="button"
            className="stack-card stack-add"
            onClick={onAdd}
            disabled={busy}
            aria-label="Add another account"
          >
            <AccountCard name="" color={nextColor(accounts)} add />
          </button>
        </div>
      )}
    </>
  );
}
