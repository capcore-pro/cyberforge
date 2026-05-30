import type { MediaSource, MediaType } from "@/lib/media-api";

export type TypeFilter = "" | MediaType;
export type SourceFilter = "" | MediaSource;

export interface MediaFiltersBarProps {
  typeFilter: TypeFilter;
  sourceFilter: SourceFilter;
  search: string;
  onTypeChange: (value: TypeFilter) => void;
  onSourceChange: (value: SourceFilter) => void;
  onSearchChange: (value: string) => void;
  trailing?: React.ReactNode;
  typeDisabled?: boolean;
}

export function MediaFiltersBar({
  typeFilter,
  sourceFilter,
  search,
  onTypeChange,
  onSourceChange,
  onSearchChange,
  trailing,
  typeDisabled = false,
}: MediaFiltersBarProps) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="flex flex-1 flex-wrap items-end gap-3">
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
            Type
          </span>
          <select
            value={typeFilter}
            disabled={typeDisabled}
            onChange={(e) => onTypeChange(e.target.value as TypeFilter)}
            className="cyber-prompt-field min-h-0 w-36 text-sm disabled:opacity-50"
          >
            <option value="">Tous</option>
            <option value="image">Images</option>
            <option value="zip">ZIPs</option>
            <option value="pdf">PDFs</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
            Source
          </span>
          <select
            value={sourceFilter}
            onChange={(e) => onSourceChange(e.target.value as SourceFilter)}
            className="cyber-prompt-field min-h-0 w-36 text-sm"
          >
            <option value="">Tous</option>
            <option value="upload">Upload</option>
            <option value="generated">Générés</option>
          </select>
        </label>
        <label className="min-w-[12rem] flex-1 space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
            Recherche
          </span>
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Filtrer par nom ou tag…"
            className="cyber-prompt-field min-h-0 w-full text-sm"
          />
        </label>
      </div>
      {trailing ? <div className="flex shrink-0 flex-wrap gap-2">{trailing}</div> : null}
    </div>
  );
}
