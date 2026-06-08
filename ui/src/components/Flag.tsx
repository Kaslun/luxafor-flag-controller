// Luxafor Flag 2 render — housing pill + translucent colour tab, with live
// brightness and effect support. Ported from the design handoff (flag.jsx).

import { useId } from "react";
import { screenSoften, applyBrightness } from "../model";

export function Flag({
  hex = "#2FCB6F",
  brightness = 0.8,
  off = false,
  effect = "solid",
  size = 116,
  blink = false,
}: {
  hex?: string;
  brightness?: number; // 0..1
  off?: boolean;
  effect?: string;
  size?: number;
  blink?: boolean;
}) {
  // Render a softened, brightness-scaled colour so it reads like the diffused
  // physical flag rather than a harsh monitor pixel.
  const base = off ? hex : screenSoften(hex);
  const shown = off ? hex : applyBrightness(base, 0.55 + 0.45 * brightness);
  const lit = off ? "#34343c" : shown;
  const bloom = off ? 0 : 0.18 + 0.34 * brightness;
  const uid = useId().replace(/:/g, "");
  const animClass = off
    ? ""
    : effect === "fade"
    ? "flag-fade"
    : effect === "strobe"
    ? "flag-strobe"
    : "";

  return (
    <div style={{ position: "relative", width: size, height: size, display: "grid", placeItems: "center" }}>
      {!off && (
        <div
          className={animClass}
          style={{
            position: "absolute",
            left: "2%",
            top: "16%",
            width: "72%",
            height: "56%",
            borderRadius: "50%",
            background: `radial-gradient(circle at 50% 50%, ${shown} 0%, transparent 66%)`,
            opacity: bloom,
            filter: "blur(8px)",
            pointerEvents: "none",
          }}
        />
      )}
      <svg width={size} height={size} viewBox="0 0 120 120" fill="none" style={{ position: "relative" }}>
        <defs>
          <linearGradient id={`body-${uid}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#26262c" />
            <stop offset="0.5" stopColor="#15151a" />
            <stop offset="1" stopColor="#0c0c10" />
          </linearGradient>
          <linearGradient id={`tab-${uid}`} x1="0" y1="0" x2="0.3" y2="1">
            <stop offset="0" stopColor={lit} stopOpacity={off ? 1 : 0.86} />
            <stop offset="1" stopColor={lit} />
          </linearGradient>
        </defs>
        <line x1="87" y1="106" x2="87" y2="122" stroke="#101014" strokeWidth="5" strokeLinecap="round" />
        <rect x="81" y="98" width="12" height="10" rx="3" fill="#1b1b20" />
        <rect x="74" y="20" width="26" height="80" rx="10" fill={`url(#body-${uid})`} stroke="#000" strokeWidth="0.5" />
        <rect x="78" y="24" width="4" height="72" rx="2" fill="#3a3a42" opacity="0.5" />
        <g className={animClass}>
          <rect
            x="22"
            y="32"
            width="58"
            height="42"
            rx="11"
            fill={off ? "#1a1a1f" : lit}
            stroke={off ? "#2a2a30" : "#000"}
            strokeOpacity={off ? 1 : 0.18}
            strokeWidth="1"
          >
            {blink && !off && (
              <animate attributeName="opacity" values="1;0.18;1" dur="1.05s" repeatCount="indefinite" />
            )}
          </rect>
          <rect x="22" y="32" width="58" height="42" rx="11" fill={`url(#tab-${uid})`}>
            {blink && !off && (
              <animate attributeName="opacity" values="1;0.18;1" dur="1.05s" repeatCount="indefinite" />
            )}
          </rect>
        </g>
      </svg>
    </div>
  );
}
