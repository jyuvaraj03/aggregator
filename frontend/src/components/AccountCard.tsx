import { useId, type CSSProperties } from "react";
import { COLORS } from "../colors";

function mix(hex: string, to: string, amount: number) {
  const a = parseInt(hex.slice(1), 16),
    b = parseInt(to.slice(1), 16);
  return (
    "#" +
    [16, 8, 0]
      .map((shift) =>
        Math.round(
          ((a >> shift) & 255) * (1 - amount) + ((b >> shift) & 255) * amount,
        )
          .toString(16)
          .padStart(2, "0"),
      )
      .join("")
  );
}
function Pattern({ color, id }: { color: number; id: string }) {
  const white = (opacity: number) => `rgba(255,255,255,${opacity})`;
  switch (color % 8) {
    case 0:
      return (
        <>
          <polygon
            points="0,0 384,0 384,124 70,118 0,150"
            fill="rgba(0,0,0,.16)"
          />
          <polygon
            points="70,118 384,124 384,216 0,216 0,150"
            fill={white(0.1)}
          />
        </>
      );
    case 1:
      return [210, 170, 130, 90, 50].map((r, i) => (
        <circle
          key={r}
          cx="340"
          cy="196"
          r={r}
          fill="none"
          stroke={white(0.05 + i * 0.02)}
          strokeWidth="16"
        />
      ));
    case 2:
      return [0, 1, 2, 3].map((i) => (
        <path
          key={i}
          d={`M0 ${120 + i * 26} C96 ${92 + i * 26},200 ${150 + i * 26},384 ${104 + i * 26} V216 H0Z`}
          fill={white(0.07)}
        />
      ));
    case 3:
      return (
        <>
          <defs>
            <pattern
              id={id}
              width="16"
              height="16"
              patternUnits="userSpaceOnUse"
            >
              <circle cx="2" cy="2" r="2" fill={white(0.22)} />
            </pattern>
            <linearGradient id={`${id}g`}>
              <stop offset="0" stopColor="#fff" stopOpacity="0" />
              <stop offset="1" stopColor="#fff" />
            </linearGradient>
            <mask id={`${id}m`}>
              <rect width="384" height="216" fill={`url(#${id}g)`} />
            </mask>
          </defs>
          <rect
            y="80"
            width="384"
            height="136"
            fill={`url(#${id})`}
            mask={`url(#${id}m)`}
          />
        </>
      );
    case 4:
      return (
        <>
          <polygon points="150,216 250,0 300,0 200,216" fill={white(0.08)} />
          <polygon
            points="230,216 330,0 400,0 400,40 310,216"
            fill={white(0.12)}
          />
          <polygon points="90,216 190,0 210,0 110,216" fill="rgba(0,0,0,.1)" />
        </>
      );
    case 5:
      return [230, 170, 110].map((r, i) => (
        <path
          key={r}
          d={`M0 ${216 - r} A${r} ${r} 0 0 1 ${r} 216 L0 216Z`}
          fill={i % 2 ? "rgba(0,0,0,.08)" : white(0.08)}
        />
      ));
    case 6:
      return [0, 1, 2, 3].map((i) => (
        <polyline
          key={i}
          points={`-10,${150 + i * 26} 120,${100 + i * 26} 250,${150 + i * 26} 394,${100 + i * 26}`}
          fill="none"
          stroke={white(0.06 + i * 0.02)}
          strokeWidth="12"
        />
      ));
    default:
      return [
        [208, 104],
        [264, 104],
        [320, 104],
        [264, 160],
        [320, 160],
        [320, 48],
      ].map(([x, y], i) => (
        <rect
          key={i}
          x={x}
          y={y}
          width="48"
          height="48"
          rx="12"
          fill={white(0.05 + (i % 3) * 0.04)}
        />
      ));
  }
}
export function AccountCard({
  name,
  color,
  add = false,
}: {
  name: string;
  color: number;
  add?: boolean;
}) {
  const id = useId().replace(/:/g, "");
  const hex = COLORS[color]?.hex ?? COLORS[0].hex;
  const style = {
    "--c": hex,
    "--c-light": mix(hex, "#ffffff", 0.18),
    "--c-dark": mix(hex, "#000000", 0.38),
    "--tint": mix(hex, "#ffffff", 0.8),
  } as CSSProperties;
  return (
    <div
      className={`account-card ${!name.trim() || add ? "silver" : "named"}`}
      style={style}
    >
      <div className="card-colour">
        <svg
          viewBox="0 0 384 216"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <Pattern color={color} id={id} />
        </svg>
      </div>
      <div className="card-silver" />
      <span className="card-name">
        {add ? "+ Add account" : name.trim() || "Account name"}
      </span>
    </div>
  );
}
