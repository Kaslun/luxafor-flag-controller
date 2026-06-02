/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        winbg: "var(--win-bg)",
        surface1: "var(--surface-1)",
        surface2: "var(--surface-2)",
        surface3: "var(--surface-3)",
        ink: "var(--text)",
        ink2: "var(--text-2)",
        ink3: "var(--text-3)",
        hairline: "var(--border)",
        accent: "var(--accent)",
      },
      fontFamily: {
        ui: "var(--font-ui)",
        display: "var(--font-display)",
        mono: "var(--font-mono)",
      },
    },
  },
  plugins: [],
};
