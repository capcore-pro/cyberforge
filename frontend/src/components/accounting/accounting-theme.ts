export const ACC_TAB_BASE =
  "border-b-2 border-transparent px-4 pb-3 pt-2 text-sm text-white/50 transition-colors hover:text-white/80";
export const ACC_TAB_ACTIVE =
  "border-[#d4a843] font-medium text-[#d4a843]";

export const PILL_BASE =
  "rounded-lg border border-white/15 bg-white/5 px-4 py-1.5 text-sm text-white/50 transition-all duration-200 hover:text-white/70";
export const PILL_ACTIVE =
  "border-[#d4a843]/50 bg-[#d4a843]/20 font-medium text-[#d4a843]";

export const GLASS_KPI =
  "rounded-xl border border-white/10 bg-[rgba(255,255,255,0.03)] p-5 backdrop-blur-xl";
export const GLASS_SECTION =
  "rounded-xl border border-white/10 bg-[rgba(255,255,255,0.03)] p-5 backdrop-blur-xl";

export const GOLD_BTN =
  "inline-flex items-center justify-center gap-2 rounded-full border border-[#d4a843] bg-[#d4a843] px-5 py-2 text-sm font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(212,168,67,0.35)] disabled:opacity-50";
export const GLASS_BTN =
  "inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm text-white/70 backdrop-blur-xl transition hover:border-[#d4a843]/50 hover:text-white disabled:opacity-50";
export const INPUT =
  "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-[#d4a843] focus:outline-none focus:ring-0";
export const SELECT = `${INPUT} appearance-none`;
export const FORM_CONTAINER =
  "rounded-xl border border-white/10 bg-white/[0.03] p-5";
export const GLASS_PILL_BTN =
  "inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-2 text-sm text-white/70 transition hover:border-white/30 hover:text-white disabled:opacity-50";
export const FIELD_LABEL =
  "mb-1 block text-xs font-semibold uppercase tracking-widest text-white/40";
export const BADGE_GLASS =
  "inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/50";

export function logAccountingApiError(context: string, message: string): void {
  console.warn(`[Comptabilité] ${context}:`, message);
}

export function shouldSilenceApiError(message: string): boolean {
  return /404|route api introuvable|introuvable/i.test(message);
}
