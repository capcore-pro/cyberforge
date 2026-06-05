export const GOLD_BTN =
  "inline-flex items-center gap-2 rounded-control border border-[#d4a843] bg-[#d4a843] px-4 py-2 text-sm font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(212,168,67,0.4)] disabled:opacity-50";
export const GLASS_SECTION =
  "rounded-card border border-white/10 bg-white/5 p-5 shadow-card backdrop-blur-xl";
export const GLASS_CARD =
  "rounded-card border border-white/10 bg-white/5 p-4 backdrop-blur-xl transition-all duration-200 hover:border-[#d4a843]/30";
export const INPUT =
  "w-full rounded-control border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-[#d4a843] focus:outline-none transition-all duration-200";
export const LABEL =
  "mb-1.5 block text-xs font-semibold uppercase tracking-wide text-white/50";
export const GHOST_BTN =
  "rounded-control border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-white/70 backdrop-blur-xl transition hover:border-white/30 hover:text-white disabled:opacity-50";
export const TAB_BASE =
  "rounded-t-control border border-transparent px-4 py-2 text-sm font-medium text-white/55 transition-all duration-200 hover:text-white";
export const TAB_ACTIVE =
  "border-white/10 border-b-transparent bg-white/5 text-[#d4a843] backdrop-blur-xl";

export function openExternalUrl(url: string): void {
  if (window.cyberforge?.openExternal) {
    void window.cyberforge.openExternal(url);
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}
