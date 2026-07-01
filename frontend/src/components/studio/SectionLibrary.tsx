import {
  getAvailableSectionTypes,
  SECTION_LABELS,
  type StudioSection,
  type StudioSectionType,
  type StudioProjectKind,
} from "@/lib/studio-types";

const PANEL =
  "flex h-full flex-col rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12] p-4";

interface SectionLibraryProps {
  projectType: StudioProjectKind | null;
  sections: StudioSection[];
  onAdd: (type: StudioSectionType) => void;
  activeSectionId: string | null;
  onSelectSection: (id: string) => void;
  disabled?: boolean;
}

export function SectionLibrary({
  projectType,
  sections,
  onAdd,
  activeSectionId,
  onSelectSection,
  disabled,
}: SectionLibraryProps) {
  const available = getAvailableSectionTypes(projectType);
  const addedTypes = new Set(sections.map((s) => s.type));

  return (
    <aside className={PANEL}>
      <p className="mb-3 font-mono text-xs text-cf-cyan">// bibliothèque</p>

      {projectType ? (
        <p className="mb-3 text-[10px] uppercase tracking-wider text-cf-muted">
          Type : {projectType}
        </p>
      ) : null}

      <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto">
        {available.map((type) => {
          const added = addedTypes.has(type);
          const section = sections.find((s) => s.type === type);
          const isActive = section?.id === activeSectionId;
          return (
            <div
              key={type}
              className={[
                "flex items-center gap-2 rounded-control border px-2 py-2",
                isActive
                  ? "border-cf-cyan/40 bg-cf-cyan/10"
                  : "border-[rgba(0,212,255,0.08)] bg-[#0d0d14]",
              ].join(" ")}
            >
              <button
                type="button"
                disabled={disabled}
                onClick={() => section && onSelectSection(section.id)}
                className="min-w-0 flex-1 truncate text-left text-xs text-cf-text"
              >
                {SECTION_LABELS[type]}
                {section?.aiGenerated ? (
                  <span className="ml-1 text-[9px] text-cf-cyan/70">✦ IA</span>
                ) : null}
              </button>
              {added ? (
                <span className="shrink-0 rounded-full border border-cf-green/30 bg-cf-green/10 px-1.5 py-0.5 text-[9px] font-semibold text-cf-green">
                  ajouté
                </span>
              ) : (
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onAdd(type)}
                  className="shrink-0 rounded border border-cf-cyan/30 px-1.5 py-0.5 text-[10px] font-semibold text-cf-cyan hover:bg-cf-cyan/10"
                  title="Ajouter la section"
                >
                  +
                </button>
              )}
            </div>
          );
        })}
      </div>

      {sections.length > 0 ? (
        <div className="mt-4 border-t border-[rgba(0,212,255,0.1)] pt-3">
          <p className="mb-2 text-[10px] uppercase tracking-wider text-cf-muted">
            Sections du projet
          </p>
          <ul className="space-y-1">
            {sections
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onSelectSection(s.id)}
                    className={[
                      "w-full truncate rounded px-2 py-1 text-left text-[11px]",
                      s.id === activeSectionId
                        ? "bg-cf-cyan/15 text-cf-cyan"
                        : "text-cf-muted hover:text-cf-text",
                    ].join(" ")}
                  >
                    {s.label}
                    {s.aiGenerated ? (
                      <span className="ml-1 text-[9px] text-cf-cyan/70">
                        ✦ IA
                      </span>
                    ) : null}
                  </button>
                </li>
              ))}
          </ul>
        </div>
      ) : null}
    </aside>
  );
}
