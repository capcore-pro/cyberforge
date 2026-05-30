/** Fallback léger pour le chargement différé des pages et onglets. */
export function PageLoader() {
  return (
    <div className="flex items-center justify-center p-12">
      <p className="animate-pulse text-sm text-cf-muted">Chargement…</p>
    </div>
  );
}
