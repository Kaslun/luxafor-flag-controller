// Stroke-icon set ported from the design's icons.jsx.

import type { CSSProperties } from "react";

export type IconName =
  | "pause"
  | "play"
  | "bolt"
  | "mic"
  | "clock"
  | "plus"
  | "minus"
  | "trash"
  | "pencil"
  | "chevron"
  | "check"
  | "x"
  | "gear"
  | "sun"
  | "moon"
  | "list"
  | "calendar"
  | "alert"
  | "download"
  | "info"
  | "power"
  | "plug"
  | "cursor"
  | "refresh"
  | "external"
  | "beacon";

const PATHS: Record<IconName, JSX.Element> = {
  pause: (
    <>
      <rect x="6" y="5" width="4" height="14" rx="1" />
      <rect x="14" y="5" width="4" height="14" rx="1" />
    </>
  ),
  play: <path d="M7 5l12 7-12 7z" />,
  bolt: <path d="M13 3 4 14h7l-1 7 9-11h-7z" />,
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l2.5 2.5" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  trash: (
    <path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m2 0v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7" />
  ),
  pencil: <path d="M4 20h4L18.5 9.5a2 2 0 0 0-3-3L5 17v3z" />,
  chevron: <path d="M6 9l6 6 6-6" />,
  check: <path d="M5 12l4.5 4.5L19 7" />,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 13a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.2A1.6 1.6 0 0 0 7 19.3a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 2.5 14H2.3a2 2 0 0 1 0-4h.2a1.6 1.6 0 0 0 1.1-2.7 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 9 2.5h.2a2 2 0 0 1 4 0V3a1.6 1.6 0 0 0 2.7 1.1 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1A1.6 1.6 0 0 0 21.5 10h.2a2 2 0 0 1 0 4h-.2a1.6 1.6 0 0 0-1.1.9z" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4a7 7 0 1 0 10.5 10.5z" />,
  list: (
    <path d="M8 6h12M8 12h12M8 18h12M3.5 6h.01M3.5 12h.01M3.5 18h.01" />
  ),
  calendar: (
    <>
      <rect x="3.5" y="5" width="17" height="16" rx="2" />
      <path d="M3.5 9h17M8 3v4M16 3v4" />
    </>
  ),
  alert: (
    <>
      <path d="M12 3 2.5 20h19z" />
      <path d="M12 10v4M12 17.5h.01" />
    </>
  ),
  download: <path d="M12 4v10m0 0 4-4m-4 4-4-4M5 19h14" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  power: <path d="M12 4v8M7 7a7 7 0 1 0 10 0" />,
  plug: <path d="M9 3v5M15 3v5M7 8h10v3a5 5 0 0 1-10 0zM12 16v5" />,
  cursor: <path d="M5 3l6 17 2.5-7L20 10.5z" />,
  refresh: (
    <path d="M4 11a8 8 0 0 1 14-4l2 2M20 13a8 8 0 0 1-14 4l-2-2M18 3v6h-6M6 21v-6h6" />
  ),
  external: (
    <path d="M14 5h5v5M19 5l-8 8M11 5H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-5" />
  ),
  beacon: <path d="M12 3v2M5.6 7.6 7 9M18.4 7.6 17 9M9 21l3-9 3 9zM8 21h8" />,
};

export function Icon({
  name,
  size = 16,
  style,
  className,
}: {
  name: IconName;
  size?: number;
  style?: CSSProperties;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
      className={className}
    >
      {PATHS[name] ?? null}
    </svg>
  );
}
