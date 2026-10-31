import { useEffect, useRef, useState } from "react";
import { COLORS } from "../colors";

export function ThemePicker({
  color,
  onChange,
  disabled,
}: {
  color: number;
  onChange: (value: number) => void;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    root.current
      ?.querySelector<HTMLButtonElement>(`[data-color="${color}"]`)
      ?.focus();
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const blur = (event: FocusEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("focusin", blur);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("focusin", blur);
    };
  }, [open, color]);
  return (
    <div className="field theme-field" ref={root}>
      <span className="field-label" id="theme-label">
        Theme
      </span>
      <button
        ref={trigger}
        className="field-control theme-trigger"
        type="button"
        aria-label={`Choose a theme colour, ${COLORS[color].name}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen(!open)}
      >
        <span
          className="theme-sample"
          style={{ background: COLORS[color].hex }}
        />
      </button>
      {open && (
        <div
          className="swatches"
          role="dialog"
          aria-labelledby="theme-label"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.stopPropagation();
              setOpen(false);
              trigger.current?.focus();
            }
            const offsets: Record<string, number> = {
              ArrowRight: 1,
              ArrowLeft: -1,
              ArrowDown: 5,
              ArrowUp: -5,
              Home: 0,
              End: 0,
            };
            if (event.key in offsets) {
              event.preventDefault();
              const current = Number(
                (document.activeElement as HTMLElement).dataset.color,
              );
              const next =
                event.key === "Home"
                  ? 0
                  : event.key === "End"
                    ? 19
                    : (current + offsets[event.key] + 20) % 20;
              root.current
                ?.querySelector<HTMLButtonElement>(`[data-color="${next}"]`)
                ?.focus();
            }
          }}
        >
          {COLORS.map((item, i) => (
            <button
              type="button"
              key={item.name}
              data-color={i}
              aria-label={item.name}
              aria-pressed={i === color}
              style={{ background: item.hex }}
              onClick={() => {
                onChange(i);
                setOpen(false);
                trigger.current?.focus();
              }}
            >
              {i === color && (
                <svg
                  viewBox="0 0 24 24"
                  width="18"
                  height="18"
                  fill="none"
                  stroke="white"
                  strokeWidth="2.5"
                  aria-hidden="true"
                >
                  <path d="m5 12 4 4L19 6" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
