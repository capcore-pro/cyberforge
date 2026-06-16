export function MobilePhoneMockup({
  primaryColor,
  secondaryColor,
  logoUrl,
  appName,
  screens,
}: {
  primaryColor: string;
  secondaryColor: string;
  logoUrl?: string | null;
  appName: string;
  screens: string[];
}) {
  const previewScreens = screens.slice(0, 3);

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox="0 0 220 440"
        className="h-[320px] w-auto drop-shadow-2xl"
        aria-label="Aperçu téléphone Android"
      >
        {/* Corps du téléphone */}
        <rect
          x="10"
          y="10"
          width="200"
          height="420"
          rx="28"
          fill="#1a1d27"
          stroke="#2a2f3d"
          strokeWidth="2"
        />
        {/* Encoche */}
        <rect x="80" y="22" width="60" height="8" rx="4" fill="#0f1117" />
        {/* Écran */}
        <rect x="20" y="40" width="180" height="360" rx="12" fill="#0f1117" />
        {/* Header */}
        <rect x="20" y="40" width="180" height="56" fill={primaryColor} opacity="0.9" />
        {logoUrl ? (
          <image href={logoUrl} x="30" y="50" width="36" height="36" clipPath="inset(0 round 8)" />
        ) : (
          <rect x="30" y="50" width="36" height="36" rx="8" fill={secondaryColor} opacity="0.8" />
        )}
        <text x="74" y="66" fill="white" fontSize="11" fontWeight="600">
          {appName.slice(0, 14)}
        </text>
        <text x="74" y="80" fill="white" fontSize="8" opacity="0.7">
          Android
        </text>
        {/* Cartes écrans */}
        {previewScreens.map((label, i) => (
          <g key={label}>
            <rect
              x="30"
              y={110 + i * 72}
              width="160"
              height="60"
              rx="10"
              fill="#1a1d27"
              stroke="#2a2f3d"
            />
            <rect
              x="38"
              y={118 + i * 72}
              width="40"
              height="4"
              rx="2"
              fill={primaryColor}
              opacity="0.8"
            />
            <text x="38" y={140 + i * 72} fill="#e5e7eb" fontSize="9" fontWeight="500">
              {label.slice(0, 18)}
            </text>
            <text x="38" y={154 + i * 72} fill="#6b7280" fontSize="7">
              Écran généré
            </text>
          </g>
        ))}
        {/* Barre navigation */}
        <rect x="20" y="372" width="180" height="28" fill="#1a1d27" />
        <circle cx="60" cy="386" r="4" fill={primaryColor} />
        <circle cx="110" cy="386" r="4" fill="#4b5563" />
        <circle cx="160" cy="386" r="4" fill="#4b5563" />
      </svg>
      <p className="mt-2 text-xs text-cf-muted">Aperçu mockup Android</p>
    </div>
  );
}
