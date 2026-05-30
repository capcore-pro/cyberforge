interface BackButtonProps {
  onClick: () => void;
  className?: string;
  label?: string;
}

/**
 * Retour vers la liste principale — bouton discret, texte or, sans bordure.
 */
export function BackButton({
  onClick,
  className = "",
  label = "Retour",
}: BackButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 border-0 bg-transparent p-0 text-sm text-cf-gold transition hover:text-cf-gold-hover focus:outline-none focus-visible:underline ${className}`}
    >
      <span aria-hidden>←</span>
      {label}
    </button>
  );
}
