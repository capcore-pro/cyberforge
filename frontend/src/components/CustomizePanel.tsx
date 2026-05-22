import { useRef } from "react";
import {
  readImageFileAsDataUrl,
  type DemoCustomization,
} from "@/lib/demo-customization";

interface CustomizePanelProps {
  value: DemoCustomization;
  onChange: (next: DemoCustomization) => void;
  previewHtml: string | null;
  previewLoading?: boolean;
  onOpenFullPreview?: () => void;
}

/** Panneau de personnalisation avant envoi démo — aperçu live intégré. */
export function CustomizePanel({
  value,
  onChange,
  previewHtml,
  previewLoading = false,
  onOpenFullPreview,
}: CustomizePanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  function patch(partial: Partial<DemoCustomization>) {
    onChange({ ...value, ...partial });
  }

  return (
    <section className="cyber-panel space-y-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
            Personnaliser
          </h2>
          <p className="mt-1 text-[10px] text-cyber-muted">
            Modifiez la démo avant envoi — l&apos;aperçu se met à jour en direct.
          </p>
        </div>
        {onOpenFullPreview ? (
          <button
            type="button"
            onClick={onOpenFullPreview}
            disabled={!previewHtml}
            className="cyber-action-btn text-[10px]"
          >
            Aperçu plein écran
          </button>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
            Titre de l&apos;application
            <input
              type="text"
              value={value.title}
              maxLength={72}
              onChange={(e) => patch({ title: e.target.value })}
              className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
              Nom utilisateur
              <input
                type="text"
                value={value.user_name}
                maxLength={48}
                onChange={(e) => patch({ user_name: e.target.value })}
                className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
              />
            </label>
            <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
              Rôle
              <input
                type="text"
                value={value.user_role}
                maxLength={48}
                onChange={(e) => patch({ user_role: e.target.value })}
                className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
              />
            </label>
          </div>

          <label className="flex flex-wrap items-center gap-3 text-[10px] uppercase tracking-wider text-cyber-muted">
            Couleur principale
            <input
              type="color"
              value={value.primary_color}
              onChange={(e) => patch({ primary_color: e.target.value })}
              className="h-10 w-14 cursor-pointer rounded border border-cyber-border bg-transparent"
            />
            <span className="font-mono normal-case text-cyber-text">
              {value.primary_color}
            </span>
          </label>

          <div>
            <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Logo client (PNG / JPG)
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (!file) return;
                  try {
                    const url = await readImageFileAsDataUrl(file);
                    patch({ logo_data_url: url });
                  } catch (err) {
                    alert(
                      err instanceof Error ? err.message : "Import logo échoué.",
                    );
                  }
                }}
              />
              <button
                type="button"
                className="cyber-action-btn text-[10px]"
                onClick={() => fileRef.current?.click()}
              >
                Choisir une image
              </button>
              {value.logo_data_url ? (
                <>
                  <img
                    src={value.logo_data_url}
                    alt="Logo"
                    className="h-10 w-10 rounded-lg border border-cyber-border object-contain"
                  />
                  <button
                    type="button"
                    className="text-[10px] text-cyber-muted underline hover:text-cyber-text"
                    onClick={() => patch({ logo_data_url: null })}
                  >
                    Retirer
                  </button>
                </>
              ) : (
                <span className="text-[10px] text-cyber-muted normal-case">
                  Remplace le logo CyberForge dans la barre latérale
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex min-h-[280px] flex-col overflow-hidden rounded-lg border border-cyber-border">
          <div className="border-b border-cyber-border px-3 py-2 text-[10px] text-cyber-muted">
            Aperçu en direct
            {previewLoading ? " · mise à jour…" : ""}
          </div>
          {previewHtml ? (
            <iframe
              title="Aperçu personnalisation"
              className="min-h-0 flex-1 bg-[#0b0f1a]"
              sandbox="allow-scripts allow-same-origin allow-forms"
              srcDoc={previewHtml}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center p-4 text-center text-xs text-cyber-muted">
              Aperçu en cours de chargement…
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
