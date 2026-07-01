import { assistField } from "@/lib/content-api";
import { useState } from "react";

interface AIAssistButtonProps {
  fieldType: string;
  context: string;
  currentValue?: string;
  onResult: (suggestion: string) => void;
  disabled?: boolean;
}

export function AIAssistButton({
  fieldType,
  context,
  currentValue = "",
  onResult,
  disabled,
}: AIAssistButtonProps) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (disabled || loading) return;
    setLoading(true);
    try {
      const suggestion = await assistField({
        field_type: fieldType,
        context,
        current_value: currentValue,
      });
      onResult(suggestion);
    } catch {
      /* silencieux — l'utilisateur peut réessayer */
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      disabled={disabled || loading}
      onClick={() => void handleClick()}
      className="shrink-0 rounded border border-cf-cyan/30 bg-cf-cyan/10 px-2 py-0.5 text-[10px] font-semibold text-cf-cyan transition hover:bg-cf-cyan/20 disabled:opacity-50"
      title="Suggestion IA"
    >
      {loading ? (
        <span className="inline-block h-3 w-3 animate-spin rounded-full border border-cf-cyan border-t-transparent" />
      ) : (
        "✦ IA"
      )}
    </button>
  );
}
