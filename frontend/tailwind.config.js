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
          border: "#1f2937",
          accent: "#06b6d4",
          accentMuted: "#0891b2",
          text: "#e5e7eb",
          muted: "#9ca3af",
        },
      },
      fontFamily: {
        sans: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
