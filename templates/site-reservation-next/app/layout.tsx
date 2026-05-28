export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body
        style={{
          fontFamily: "system-ui",
          margin: 0,
          background: "#0a0a0f",
          color: "#e5e7eb",
        }}
      >
        <div style={{ padding: 24, maxWidth: 980, margin: "0 auto" }}>{children}</div>
      </body>
    </html>
  );
}

