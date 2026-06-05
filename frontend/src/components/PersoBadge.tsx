/** Badge distinctif projets personnels Mat. */
export function PersoBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border border-[#d4a843]/40 bg-[#d4a843]/20 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-[#d4a843] ${className}`}
    >
      PERSO
    </span>
  );
}
