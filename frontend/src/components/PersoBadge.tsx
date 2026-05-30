/** Badge distinctif projets personnels Mat (cyan/fuchsia vs or client). */
export function PersoBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block rounded-full border border-fuchsia-400/50 bg-fuchsia-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-fuchsia-200 ${className}`}
    >
      PERSO
    </span>
  );
}
