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
        <div style={{ padding: 24, maxWidth: 980, margin: "0 auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <a href="/" style={{ color: "#e5e7eb", textDecoration: "none", fontWeight: 700 }}>
              Boutique
            </a>
            <a href="/cart" style={{ color: "#e5e7eb", textDecoration: "none" }}>
              Panier
            </a>
          </div>
          <div style={{ height: 16 }} />
          {children}
        </div>
      </body>
    </html>
  );
}

