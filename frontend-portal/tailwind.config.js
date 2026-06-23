/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        portal: {
          bg: "#0a0a0f",
          card: "#12121a",
          border: "#2a2a3a",
          accent: "#6366f1",
          text: "#f4f4f5",
          muted: "#a1a1aa",
        },
      },
    },
  },
  plugins: [],
};
