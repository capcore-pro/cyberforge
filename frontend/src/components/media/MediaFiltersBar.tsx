import {
  FIELD_LABEL,
  INPUT,
  SELECT,
} from "@/components/accounting/accounting-theme";
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
    <div className="flex flex-col gap-4 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 lg:flex-row lg:items-end lg:justify-between">
      <div className="flex flex-1 flex-wrap items-end gap-4">
        <label className="space-y-1">
          <span className={FIELD_LABEL}>Type</span>
          <select
            value={typeFilter}
            disabled={typeDisabled}
            onChange={(e) => onTypeChange(e.target.value as TypeFilter)}
            className={`${SELECT} w-36 cursor-pointer disabled:opacity-50`}
          >
            <option value="">Tous</option>
            <option value="image">Images</option>
            <option value="zip">ZIPs</option>
            <option value="pdf">PDFs</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className={FIELD_LABEL}>Source</span>
          <select
            value={sourceFilter}
            onChange={(e) => onSourceChange(e.target.value as SourceFilter)}
            className={`${SELECT} w-36 cursor-pointer`}
          >
            <option value="">Tous</option>
            <option value="upload">Upload</option>
            <option value="generated">Générés</option>
          </select>
        </label>
        <label className="min-w-[12rem] flex-1 space-y-1">
          <span className={FIELD_LABEL}>Recherche</span>
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Filtrer par nom ou tag…"
            className={INPUT}
          />
        </label>
      </div>
      {trailing ? (
        <div className="flex shrink-0 flex-wrap gap-2">
          {trailing}
        </div>
      ) : null}
    </div>
  );
}
