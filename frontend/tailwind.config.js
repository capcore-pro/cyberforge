/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Palette CyberForge — thème sombre orienté sécurité
        cyber: {
          bg: "#0a0e17",
          surface: "#111827",
          surfaceAlt: "#0d1220",
          border: "#1f2937",
          borderGlow: "#4c1d95",
          accent: "#06b6d4",
          accentMuted: "#0891b2",
          violet: "#a855f7",
          violetMuted: "#7c3aed",
          neon: "#22d3ee",
          text: "#e5e7eb",
          muted: "#9ca3af",
        },
      },
      boxShadow: {
        neonCyan: "0 0 20px rgba(6, 182, 212, 0.35), 0 0 40px rgba(6, 182, 212, 0.15)",
        neonViolet: "0 0 20px rgba(168, 85, 247, 0.35), 0 0 40px rgba(168, 85, 247, 0.15)",
        card: "0 0 0 1px rgba(168, 85, 247, 0.2), inset 0 1px 0 rgba(34, 211, 238, 0.08)",
      },
      backgroundImage: {
        "cyber-grid":
          "linear-gradient(rgba(168, 85, 247, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 182, 212, 0.06) 1px, transparent 1px)",
      },
      backgroundSize: {
        "cyber-grid": "32px 32px",
      },
      animation: {
        glitch: "glitch 3s infinite",
        pulseNeon: "pulseNeon 2.5s ease-in-out infinite",
        scan: "scan 4s linear infinite",
      },
      keyframes: {
        glitch: {
          "0%, 100%": { transform: "translate(0)" },
          "20%": { transform: "translate(-2px, 1px)" },
          "40%": { transform: "translate(2px, -1px)" },
          "60%": { transform: "translate(-1px, -1px)" },
          "80%": { transform: "translate(1px, 1px)" },
        },
        pulseNeon: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.65" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
      },
      fontFamily: {
        sans: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
