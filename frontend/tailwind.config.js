/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cf: {
          main: "#0d0d0d",
          sidebar: "#111111",
          card: "#111111",
          secondary: "#161616",
          active: "#1c1a12",
          border: "#222222",
          "border-input": "#2a2a2a",
          gold: "#c9a84c",
          "gold-hover": "#e0be6a",
          "gold-subtle": "#1c1a12",
          text: "#f0f0f0",
          body: "#cccccc",
          muted: "#888888",
          tertiary: "#444444",
          label: "#666666",
          success: "#4caf50",
          alert: "#e8a020",
          info: "#5b8dd9",
        },
        cyber: {
          bg: "#0d0d0d",
          surface: "#111111",
          surfaceAlt: "#111111",
          border: "#222222",
          borderGlow: "#c9a84c",
          accent: "#c9a84c",
          accentMuted: "#e0be6a",
          violet: "#c9a84c",
          violetMuted: "#e0be6a",
          neon: "#c9a84c",
          text: "#f0f0f0",
          muted: "#888888",
        },
      },
      borderRadius: {
        card: "10px",
        control: "8px",
      },
      fontFamily: {
        sans: [
          "Inter",
          "Segoe UI",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      fontSize: {
        body: ["13px", { lineHeight: "1.5" }],
        label: ["11px", { lineHeight: "1.4", letterSpacing: "0.06em" }],
      },
      boxShadow: {
        card: "0 1px 0 rgba(255, 255, 255, 0.04) inset",
        gold: "0 0 0 1px rgba(201, 168, 76, 0.25)",
      },
    },
  },
  plugins: [],
};
