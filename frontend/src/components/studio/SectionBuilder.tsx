import { useRef, useState } from "react";
import { generateSocialVisual, uploadReferenceImage } from "@/lib/visual-api";
import type { StudioSection } from "@/lib/studio-types";
import { AIAssistButton } from "@/components/studio/AIAssistButton";
import {
  EMPTY_FAQ,
  EMPTY_FONCTIONNALITE,
  EMPTY_PRODUCT,
  EMPTY_REALISATION,
  EMPTY_SERVICE,
  EMPTY_TEMOIGNAGE,
  parseJsonArray,
  stringifyJsonArray,
  type FaqItem,
  type FonctionnaliteItem,
  type ProductItem,
  type RealisationItem,
  type ServiceItem,
  type TemoignageItem,
} from "@/lib/studio-section-json";

const INPUT =
  "w-full rounded-control border border-[rgba(0,212,255,0.15)] bg-[#0d0d14] px-3 py-2 text-sm text-cf-text placeholder:text-cf-muted focus:border-cf-cyan/50 focus:outline-none";

const BTN_ADD =
  "rounded border border-cf-cyan/30 bg-cf-cyan/5 px-2 py-1 text-[10px] font-semibold text-cf-cyan hover:bg-cf-cyan/10";

export interface SectionChangeOptions {
  imageUrl?: string;
  fromAI?: boolean;
}

interface SectionBuilderProps {
  section: StudioSection | null;
  context: string;
  onChange: (
    sectionId: string,
    fields: Record<string, string>,
    options?: SectionChangeOptions,
  ) => void;
  disabled?: boolean;
}

function FieldRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
        {label}
      </span>
      {children}
    </label>
  );
}

function TextField({
  label,
  fieldType,
  value,
  maxLength,
  context,
  onChange,
  disabled,
  multiline,
  withAI = true,
}: {
  label: string;
  fieldType: string;
  value: string;
  maxLength?: number;
  context: string;
  onChange: (v: string, fromAI?: boolean) => void;
  disabled?: boolean;
  multiline?: boolean;
  withAI?: boolean;
}) {
  const InputTag = multiline ? "textarea" : "input";
  return (
    <FieldRow label={label}>
      <div className="flex gap-2">
        <InputTag
          value={value}
          maxLength={maxLength}
          rows={multiline ? 4 : undefined}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className={[INPUT, multiline ? "resize-y" : ""].join(" ")}
        />
        {withAI ? (
          <AIAssistButton
            fieldType={fieldType}
            context={context}
            currentValue={value}
            onResult={(v) => onChange(v, true)}
            disabled={disabled}
          />
        ) : null}
      </div>
    </FieldRow>
  );
}

function PlainField({
  label,
  value,
  onChange,
  disabled,
  type = "text",
  multiline,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  type?: string;
  multiline?: boolean;
}) {
  const InputTag = multiline ? "textarea" : "input";
  return (
    <FieldRow label={label}>
      <InputTag
        type={multiline ? undefined : type}
        value={value}
        rows={multiline ? 4 : undefined}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={[INPUT, multiline ? "resize-y" : ""].join(" ")}
      />
    </FieldRow>
  );
}

function ImageField({
  label,
  value,
  context,
  onChange,
  disabled,
  importOnly,
}: {
  label: string;
  value: string;
  context: string;
  onChange: (url: string) => void;
  disabled?: boolean;
  importOnly?: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [fluxLoading, setFluxLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);

  async function handleFlux() {
    if (disabled || fluxLoading || importOnly) return;
    setFluxLoading(true);
    try {
      const res = await generateSocialVisual({
        texte_principal: context.slice(0, 80) || label,
        sous_texte: value || "Visuel professionnel",
        format_key: "1:1",
        style: "professionnel",
        pose_key: "default",
      });
      if (res.success && res.image_url) {
        onChange(res.image_url);
      }
    } finally {
      setFluxLoading(false);
    }
  }

  async function handleUpload(file: File) {
    if (disabled || uploadLoading) return;
    setUploadLoading(true);
    try {
      const res = await uploadReferenceImage(file);
      onChange(res.reference_url);
    } finally {
      setUploadLoading(false);
    }
  }

  return (
    <FieldRow label={label}>
      <div className="space-y-2">
        <input
          type="url"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          placeholder="https://…"
          className={INPUT}
        />
        <div className="flex flex-wrap gap-2">
          {!importOnly ? (
            <button
              type="button"
              disabled={disabled || fluxLoading}
              onClick={() => void handleFlux()}
              className="rounded border border-cf-cyan/30 bg-cf-cyan/10 px-2 py-1 text-[10px] font-semibold text-cf-cyan"
            >
              {fluxLoading ? "…" : "✦ FLUX"}
            </button>
          ) : null}
          <button
            type="button"
            disabled={disabled || uploadLoading}
            onClick={() => fileRef.current?.click()}
            className="rounded border border-[rgba(0,212,255,0.2)] px-2 py-1 text-[10px] font-semibold text-cf-muted"
          >
            {uploadLoading ? "…" : "📤 Importer"}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleUpload(file);
            }}
          />
        </div>
        {value ? (
          <img
            src={value}
            alt=""
            className="h-20 w-20 rounded border border-[rgba(0,212,255,0.15)] object-cover"
          />
        ) : null}
      </div>
    </FieldRow>
  );
}

function ListShell({
  index,
  canRemove,
  onRemove,
  disabled,
  children,
}: {
  index: number;
  canRemove: boolean;
  onRemove: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2 rounded-control border border-[rgba(0,212,255,0.1)] bg-[#0d0d14] p-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-cf-muted">#{index + 1}</span>
        {canRemove ? (
          <button
            type="button"
            disabled={disabled}
            onClick={onRemove}
            className="text-xs text-cf-muted hover:text-cf-red"
            title="Supprimer"
          >
            🗑️
          </button>
        ) : null}
      </div>
      {children}
    </div>
  );
}

export function SectionBuilder({
  section,
  context,
  onChange,
  disabled,
}: SectionBuilderProps) {
  if (!section) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center rounded-[10px] border border-dashed border-[rgba(0,212,255,0.15)] bg-[#0a0a12] p-6 text-center text-sm text-cf-muted">
        Ajoutez une section depuis la bibliothèque ou sélectionnez-en une pour
        commencer.
      </div>
    );
  }

  function patch(
    fields: Partial<Record<string, string>>,
    opts?: SectionChangeOptions,
  ) {
    onChange(section.id, { ...section.fields, ...fields }, opts);
  }

  function patchAI(fields: Partial<Record<string, string>>) {
    patch(fields, { fromAI: true });
  }

  const previewLabel =
    section.fields.titre ||
    section.fields.titre_section ||
    section.fields.description_fr ||
    section.fields.nom_logiciel ||
    section.label;

  return (
    <div className="flex h-full flex-col rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12] p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h3 className="font-mono text-sm text-cf-cyan">// {section.label}</h3>
        {section.animationClass ? (
          <span className="font-mono text-[10px] text-cf-muted">
            {section.animationClass}
          </span>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {section.type === "hero" ? (
          <>
            <TextField
              label="Titre"
              fieldType="titre"
              value={section.fields.titre ?? ""}
              maxLength={80}
              context={context}
              onChange={(v, fromAI) =>
                fromAI ? patchAI({ titre: v }) : patch({ titre: v })
              }
              disabled={disabled}
            />
            <TextField
              label="Slogan"
              fieldType="slogan"
              value={section.fields.slogan ?? ""}
              maxLength={120}
              context={context}
              onChange={(v, fromAI) =>
                fromAI ? patchAI({ slogan: v }) : patch({ slogan: v })
              }
              disabled={disabled}
            />
            <TextField
              label="CTA"
              fieldType="cta"
              value={section.fields.cta_label ?? ""}
              maxLength={30}
              context={context}
              onChange={(v, fromAI) =>
                fromAI ? patchAI({ cta_label: v }) : patch({ cta_label: v })
              }
              disabled={disabled}
            />
            <FieldRow label="URL du CTA">
              <input
                type="url"
                value={section.fields.cta_url ?? ""}
                disabled={disabled}
                onChange={(e) => patch({ cta_url: e.target.value })}
                className={INPUT}
              />
            </FieldRow>
            <ImageField
              label="Image de fond"
              value={section.fields.image_fond ?? section.imageUrl ?? ""}
              context={context}
              onChange={(url) => patch({ image_fond: url }, { imageUrl: url })}
              disabled={disabled}
            />
            <TextField
              label="Bouton secondaire"
              fieldType="cta"
              value={section.fields.bouton_secondaire ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ bouton_secondaire: v })
                  : patch({ bouton_secondaire: v })
              }
              disabled={disabled}
            />
          </>
        ) : null}

        {section.type === "services" ? (
          <>
            <TextField
              label="Titre de la section"
              fieldType="titre"
              value={section.fields.titre_section ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ titre_section: v })
                  : patch({ titre_section: v })
              }
              disabled={disabled}
            />
            {(() => {
              const items = parseJsonArray<ServiceItem>(
                section.fields.services,
                [EMPTY_SERVICE],
              );
              const update = (next: ServiceItem[], fromAI?: boolean) => {
                const data = { services: stringifyJsonArray(next) };
                fromAI ? patchAI(data) : patch(data);
              };
              return (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
                    Services ({items.length}/8)
                  </span>
                  {items.map((item, i) => (
                    <ListShell
                      key={i}
                      index={i}
                      canRemove={items.length > 1}
                      disabled={disabled}
                      onRemove={() =>
                        update(items.filter((_, j) => j !== i))
                      }
                    >
                      <PlainField
                        label="Nom"
                        value={item.nom}
                        disabled={disabled}
                        onChange={(v) => {
                          const next = [...items];
                          next[i] = { ...item, nom: v };
                          update(next);
                        }}
                      />
                      <FieldRow label="Description">
                        <div className="flex gap-2">
                          <textarea
                            value={item.description}
                            rows={3}
                            disabled={disabled}
                            onChange={(e) => {
                              const next = [...items];
                              next[i] = { ...item, description: e.target.value };
                              update(next);
                            }}
                            className={[INPUT, "resize-y"].join(" ")}
                          />
                          <AIAssistButton
                            fieldType="service"
                            context={context}
                            currentValue={item.description}
                            onResult={(v) => {
                              const next = [...items];
                              next[i] = { ...item, description: v };
                              update(next, true);
                            }}
                            disabled={disabled}
                          />
                        </div>
                      </FieldRow>
                      <div className="grid grid-cols-2 gap-2">
                        <PlainField
                          label="Prix"
                          value={item.prix}
                          disabled={disabled}
                          onChange={(v) => {
                            const next = [...items];
                            next[i] = { ...item, prix: v };
                            update(next);
                          }}
                        />
                        <PlainField
                          label="Icône"
                          value={item.icone}
                          disabled={disabled}
                          onChange={(v) => {
                            const next = [...items];
                            next[i] = { ...item, icone: v };
                            update(next);
                          }}
                        />
                      </div>
                    </ListShell>
                  ))}
                  {items.length < 8 ? (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => update([...items, { ...EMPTY_SERVICE }])}
                      className={BTN_ADD}
                    >
                      ➕ Ajouter un service
                    </button>
                  ) : null}
                </div>
              );
            })()}
          </>
        ) : null}

        {section.type === "catalogue" ? (
          <>
            <TextField
              label="Titre de la section"
              fieldType="titre"
              value={section.fields.titre_section ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ titre_section: v })
                  : patch({ titre_section: v })
              }
              disabled={disabled}
            />
            {(() => {
              const items = parseJsonArray<ProductItem>(
                section.fields.produits,
                [EMPTY_PRODUCT],
              );
              const update = (next: ProductItem[], fromAI?: boolean) => {
                const data = { produits: stringifyJsonArray(next) };
                fromAI ? patchAI(data) : patch(data);
              };
              return (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
                    Produits ({items.length}/20)
                  </span>
                  {items.map((item, i) => (
                    <ListShell
                      key={i}
                      index={i}
                      canRemove={items.length > 1}
                      disabled={disabled}
                      onRemove={() =>
                        update(items.filter((_, j) => j !== i))
                      }
                    >
                      <PlainField
                        label="Nom"
                        value={item.nom}
                        disabled={disabled}
                        onChange={(v) => {
                          const next = [...items];
                          next[i] = { ...item, nom: v };
                          update(next);
                        }}
                      />
                      <FieldRow label="Description">
                        <div className="flex gap-2">
                          <textarea
                            value={item.description}
                            rows={3}
                            disabled={disabled}
                            onChange={(e) => {
                              const next = [...items];
                              next[i] = { ...item, description: e.target.value };
                              update(next);
                            }}
                            className={[INPUT, "resize-y"].join(" ")}
                          />
                          <AIAssistButton
                            fieldType="description"
                            context={context}
                            currentValue={item.description}
                            onResult={(v) => {
                              const next = [...items];
                              next[i] = { ...item, description: v };
                              update(next, true);
                            }}
                            disabled={disabled}
                          />
                        </div>
                      </FieldRow>
                      <div className="grid grid-cols-2 gap-2">
                        <PlainField
                          label="Prix"
                          value={item.prix}
                          disabled={disabled}
                          onChange={(v) => {
                            const next = [...items];
                            next[i] = { ...item, prix: v };
                            update(next);
                          }}
                        />
                        <FieldRow label="Statut">
                          <select
                            value={item.statut}
                            disabled={disabled}
                            onChange={(e) => {
                              const next = [...items];
                              next[i] = {
                                ...item,
                                statut: e.target
                                  .value as ProductItem["statut"],
                              };
                              update(next);
                            }}
                            className={INPUT}
                          >
                            <option value="Disponible">Disponible</option>
                            <option value="Bientôt disponible">
                              Bientôt disponible
                            </option>
                            <option value="Épuisé">Épuisé</option>
                          </select>
                        </FieldRow>
                      </div>
                    </ListShell>
                  ))}
                  {items.length < 20 ? (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => update([...items, { ...EMPTY_PRODUCT }])}
                      className={BTN_ADD}
                    >
                      ➕ Ajouter un produit
                    </button>
                  ) : null}
                </div>
              );
            })()}
          </>
        ) : null}

        {section.type === "faq" ? (
          <>
            <TextField
              label="Titre de la section"
              fieldType="titre"
              value={section.fields.titre_section ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ titre_section: v })
                  : patch({ titre_section: v })
              }
              disabled={disabled}
            />
            {(() => {
              const items = parseJsonArray<FaqItem>(
                section.fields.faq,
                [EMPTY_FAQ],
              );
              const update = (next: FaqItem[], fromAI?: boolean) => {
                const data = { faq: stringifyJsonArray(next) };
                fromAI ? patchAI(data) : patch(data);
              };
              return (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
                    Questions ({items.length}/15)
                  </span>
                  {items.map((item, i) => (
                    <ListShell
                      key={i}
                      index={i}
                      canRemove={items.length > 1}
                      disabled={disabled}
                      onRemove={() =>
                        update(items.filter((_, j) => j !== i))
                      }
                    >
                      <FieldRow label="Question">
                        <div className="flex gap-2">
                          <input
                            value={item.question}
                            disabled={disabled}
                            onChange={(e) => {
                              const next = [...items];
                              next[i] = { ...item, question: e.target.value };
                              update(next);
                            }}
                            className={INPUT}
                          />
                          <AIAssistButton
                            fieldType="faq_question"
                            context={context}
                            currentValue={item.question}
                            onResult={(v) => {
                              const next = [...items];
                              next[i] = { ...item, question: v };
                              update(next, true);
                            }}
                            disabled={disabled}
                          />
                        </div>
                      </FieldRow>
                      <FieldRow label="Réponse">
                        <div className="flex gap-2">
                          <textarea
                            value={item.reponse}
                            rows={3}
                            disabled={disabled}
                            onChange={(e) => {
                              const next = [...items];
                              next[i] = { ...item, reponse: e.target.value };
                              update(next);
                            }}
                            className={[INPUT, "resize-y"].join(" ")}
                          />
                          <AIAssistButton
                            fieldType="faq_reponse"
                            context={context}
                            currentValue={item.reponse}
                            onResult={(v) => {
                              const next = [...items];
                              next[i] = { ...item, reponse: v };
                              update(next, true);
                            }}
                            disabled={disabled}
                          />
                        </div>
                      </FieldRow>
                    </ListShell>
                  ))}
                  {items.length < 15 ? (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => update([...items, { ...EMPTY_FAQ }])}
                      className={BTN_ADD}
                    >
                      ➕ Ajouter une question
                    </button>
                  ) : null}
                </div>
              );
            })()}
          </>
        ) : null}

        {section.type === "temoignages" ? (
          <>
            <TextField
              label="Titre de la section"
              fieldType="titre"
              value={section.fields.titre_section ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ titre_section: v })
                  : patch({ titre_section: v })
              }
              disabled={disabled}
            />
            {(() => {
              const items = parseJsonArray<TemoignageItem>(
                section.fields.temoignages,
                [EMPTY_TEMOIGNAGE],
              );
              const update = (next: TemoignageItem[], fromAI?: boolean) => {
                const data = { temoignages: stringifyJsonArray(next) };
                fromAI ? patchAI(data) : patch(data);
              };
              return (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
                    Témoignages ({items.length}/10)
                  </span>
                  {items.map((item, i) => (
                    <ListShell
                      key={i}
                      index={i}
                      canRemove={items.length > 1}
                      disabled={disabled}
                      onRemove={() =>
                        update(items.filter((_, j) => j !== i))
                      }
                    >
                      <div className="grid grid-cols-2 gap-2">
                        <PlainField
                          label="Nom client"
                          value={item.nom_client}
                          disabled={disabled}
                          onChange={(v) => {
                            const next = [...items];
                            next[i] = { ...item, nom_client: v };
                            update(next);
                          }}
                        />
                        <PlainField
                          label="Poste"
                          value={item.poste}
                          disabled={disabled}
                          onChange={(v) => {
                            const next = [...items];
                            next[i] = { ...item, poste: v };
                            update(next);
                          }}
                        />
                      </div>
                      <FieldRow label="Texte">
                        <div className="flex gap-2">
                          <textarea
                            value={item.texte}
                            rows={3}
                            disabled={disabled}
                            onChange={(e) => {
                              const next = [...items];
                              next[i] = { ...item, texte: e.target.value };
                              update(next);
                            }}
                            className={[INPUT, "resize-y"].join(" ")}
                          />
                          <AIAssistButton
                            fieldType="temoignage"
                            context={context}
                            currentValue={item.texte}
                            onResult={(v) => {
                              const next = [...items];
                              next[i] = { ...item, texte: v };
                              update(next, true);
                            }}
                            disabled={disabled}
                          />
                        </div>
                      </FieldRow>
                      <FieldRow label="Note">
                        <select
                          value={item.note}
                          disabled={disabled}
                          onChange={(e) => {
                            const next = [...items];
                            next[i] = { ...item, note: e.target.value };
                            update(next);
                          }}
                          className={INPUT}
                        >
                          {[1, 2, 3, 4, 5].map((n) => (
                            <option key={n} value={String(n)}>
                              {n} étoile{n > 1 ? "s" : ""}
                            </option>
                          ))}
                        </select>
                      </FieldRow>
                    </ListShell>
                  ))}
                  {items.length < 10 ? (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() =>
                        update([...items, { ...EMPTY_TEMOIGNAGE }])
                      }
                      className={BTN_ADD}
                    >
                      ➕ Ajouter
                    </button>
                  ) : null}
                </div>
              );
            })()}
          </>
        ) : null}

        {section.type === "realisations" ? (
          <>
            <TextField
              label="Titre de la section"
              fieldType="titre"
              value={section.fields.titre_section ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ titre_section: v })
                  : patch({ titre_section: v })
              }
              disabled={disabled}
            />
            <PlainField
              label="Texte placeholder"
              value={
                section.fields.texte_placeholder ??
                "Nos premières réalisations arrivent bientôt"
              }
              disabled={disabled}
              multiline
              onChange={(v) => patch({ texte_placeholder: v })}
            />
            {(() => {
              const items = parseJsonArray<RealisationItem>(
                section.fields.projets,
                [],
              );
              const update = (next: RealisationItem[]) =>
                patch({ projets: stringifyJsonArray(next) });
              return (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
                    Projets optionnels ({items.length}/6)
                  </span>
                  {items.map((item, i) => (
                    <ListShell
                      key={i}
                      index={i}
                      canRemove
                      disabled={disabled}
                      onRemove={() =>
                        update(items.filter((_, j) => j !== i))
                      }
                    >
                      <PlainField
                        label="Titre"
                        value={item.titre}
                        disabled={disabled}
                        onChange={(v) => {
                          const next = [...items];
                          next[i] = { ...item, titre: v };
                          update(next);
                        }}
                      />
                      <PlainField
                        label="Description"
                        value={item.description}
                        disabled={disabled}
                        multiline
                        onChange={(v) => {
                          const next = [...items];
                          next[i] = { ...item, description: v };
                          update(next);
                        }}
                      />
                      <ImageField
                        label="Image"
                        value={item.image_url}
                        context={context}
                        importOnly
                        disabled={disabled}
                        onChange={(url) => {
                          const next = [...items];
                          next[i] = { ...item, image_url: url };
                          update(next);
                        }}
                      />
                    </ListShell>
                  ))}
                  {items.length < 6 ? (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() =>
                        update([...items, { ...EMPTY_REALISATION }])
                      }
                      className={BTN_ADD}
                    >
                      ➕ Ajouter un projet
                    </button>
                  ) : null}
                </div>
              );
            })()}
          </>
        ) : null}

        {section.type === "about" ? (
          <>
            <TextField
              label="Titre"
              fieldType="titre"
              value={section.fields.titre ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI ? patchAI({ titre: v }) : patch({ titre: v })
              }
              disabled={disabled}
            />
            <TextField
              label="Texte présentation"
              fieldType="presentation"
              value={section.fields.texte ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI ? patchAI({ texte: v }) : patch({ texte: v })
              }
              disabled={disabled}
              multiline
            />
            <PlainField
              label="Valeurs (une par ligne)"
              value={section.fields.valeurs ?? ""}
              disabled={disabled}
              multiline
              onChange={(v) => patch({ valeurs: v })}
            />
            <ImageField
              label="Photo équipe"
              value={section.fields.photo_equipe ?? ""}
              context={context}
              onChange={(url) => patch({ photo_equipe: url }, { imageUrl: url })}
              disabled={disabled}
            />
          </>
        ) : null}

        {section.type === "contact" ? (
          <>
            <FieldRow label="Email">
              <input
                type="email"
                value={section.fields.email ?? ""}
                disabled={disabled}
                onChange={(e) => patch({ email: e.target.value })}
                className={INPUT}
              />
            </FieldRow>
            <FieldRow label="Téléphone">
              <input
                type="tel"
                value={section.fields.telephone ?? ""}
                disabled={disabled}
                onChange={(e) => patch({ telephone: e.target.value })}
                className={INPUT}
              />
            </FieldRow>
            <FieldRow label="Adresse">
              <input
                type="text"
                value={section.fields.adresse ?? ""}
                disabled={disabled}
                onChange={(e) => patch({ adresse: e.target.value })}
                className={INPUT}
              />
            </FieldRow>
            <label className="flex items-center gap-2 text-xs text-cf-muted">
              <input
                type="checkbox"
                checked={section.fields.formulaire_actif === "true"}
                disabled={disabled}
                onChange={(e) =>
                  patch({
                    formulaire_actif: e.target.checked ? "true" : "false",
                  })
                }
              />
              Formulaire de contact actif
            </label>
            <label className="flex items-center gap-2 text-xs text-cf-muted">
              <input
                type="checkbox"
                checked={section.fields.google_maps === "true"}
                disabled={disabled}
                onChange={(e) =>
                  patch({ google_maps: e.target.checked ? "true" : "false" })
                }
              />
              Afficher Google Maps
            </label>
          </>
        ) : null}

        {section.type === "panier" ? (
          <>
            <PlainField
              label="Texte bouton panier"
              value={section.fields.texte_bouton ?? ""}
              disabled={disabled}
              onChange={(v) => patch({ texte_bouton: v })}
            />
            <FieldRow label="Devise">
              <select
                value={section.fields.devise ?? "EUR"}
                disabled={disabled}
                onChange={(e) => patch({ devise: e.target.value })}
                className={INPUT}
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
                <option value="GBP">GBP</option>
              </select>
            </FieldRow>
            <PlainField
              label="Message livraison"
              value={section.fields.message_livraison ?? ""}
              disabled={disabled}
              onChange={(v) => patch({ message_livraison: v })}
            />
            <label className="flex items-center gap-2 text-xs text-cf-muted">
              <input
                type="checkbox"
                checked={section.fields.stripe_actif === "true"}
                disabled={disabled}
                onChange={(e) =>
                  patch({
                    stripe_actif: e.target.checked ? "true" : "false",
                  })
                }
              />
              Stripe actif
            </label>
          </>
        ) : null}

        {section.type === "checkout" ? (
          <>
            <FieldRow label="Clé Stripe publishable">
              <input
                type="password"
                value={section.fields.stripe_publishable_key ?? ""}
                disabled={disabled}
                onChange={(e) =>
                  patch({ stripe_publishable_key: e.target.value })
                }
                placeholder="pk_live_…"
                className={INPUT}
              />
            </FieldRow>
            <PlainField
              label="Message de confirmation"
              value={section.fields.message_confirmation ?? ""}
              disabled={disabled}
              onChange={(v) => patch({ message_confirmation: v })}
            />
            <FieldRow label="Redirect après paiement (URL)">
              <input
                type="url"
                value={section.fields.redirect_url ?? ""}
                disabled={disabled}
                onChange={(e) => patch({ redirect_url: e.target.value })}
                className={INPUT}
              />
            </FieldRow>
          </>
        ) : null}

        {section.type === "dashboard_app" ? (
          <>
            <PlainField
              label="Modules disponibles (un par ligne)"
              value={section.fields.modules ?? ""}
              disabled={disabled}
              multiline
              onChange={(v) => patch({ modules: v })}
            />
            <TextField
              label="Description dashboard"
              fieldType="description"
              value={section.fields.description_dashboard ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ description_dashboard: v })
                  : patch({ description_dashboard: v })
              }
              disabled={disabled}
              multiline
            />
          </>
        ) : null}

        {section.type === "auth" ? (
          <>
            <FieldRow label="Type auth">
              <select
                value={section.fields.type_auth ?? "email"}
                disabled={disabled}
                onChange={(e) => patch({ type_auth: e.target.value })}
                className={INPUT}
              >
                <option value="email">Email/Mot de passe</option>
                <option value="google">Google</option>
                <option value="magic_link">Magic link</option>
              </select>
            </FieldRow>
            <TextField
              label="Texte page login"
              fieldType="description"
              value={section.fields.texte_login ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ texte_login: v })
                  : patch({ texte_login: v })
              }
              disabled={disabled}
              multiline
            />
            <PlainField
              label="Rôles utilisateurs (un par ligne)"
              value={section.fields.roles ?? ""}
              disabled={disabled}
              multiline
              onChange={(v) => patch({ roles: v })}
            />
          </>
        ) : null}

        {section.type === "fonctionnalites" ? (
          <>
            {(() => {
              const items = parseJsonArray<FonctionnaliteItem>(
                section.fields.fonctionnalites,
                [EMPTY_FONCTIONNALITE],
              );
              const update = (next: FonctionnaliteItem[], fromAI?: boolean) => {
                const data = { fonctionnalites: stringifyJsonArray(next) };
                fromAI ? patchAI(data) : patch(data);
              };
              return (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
                    Fonctionnalités ({items.length}/12)
                  </span>
                  {items.map((item, i) => (
                    <ListShell
                      key={i}
                      index={i}
                      canRemove={items.length > 1}
                      disabled={disabled}
                      onRemove={() =>
                        update(items.filter((_, j) => j !== i))
                      }
                    >
                      <div className="grid grid-cols-2 gap-2">
                        <PlainField
                          label="Icône"
                          value={item.icone}
                          disabled={disabled}
                          onChange={(v) => {
                            const next = [...items];
                            next[i] = { ...item, icone: v };
                            update(next);
                          }}
                        />
                        <PlainField
                          label="Titre"
                          value={item.titre}
                          disabled={disabled}
                          onChange={(v) => {
                            const next = [...items];
                            next[i] = { ...item, titre: v };
                            update(next);
                          }}
                        />
                      </div>
                      <FieldRow label="Description">
                        <div className="flex gap-2">
                          <textarea
                            value={item.description}
                            rows={3}
                            disabled={disabled}
                            onChange={(e) => {
                              const next = [...items];
                              next[i] = { ...item, description: e.target.value };
                              update(next);
                            }}
                            className={[INPUT, "resize-y"].join(" ")}
                          />
                          <AIAssistButton
                            fieldType="description"
                            context={context}
                            currentValue={item.description}
                            onResult={(v) => {
                              const next = [...items];
                              next[i] = { ...item, description: v };
                              update(next, true);
                            }}
                            disabled={disabled}
                          />
                        </div>
                      </FieldRow>
                    </ListShell>
                  ))}
                  {items.length < 12 ? (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() =>
                        update([...items, { ...EMPTY_FONCTIONNALITE }])
                      }
                      className={BTN_ADD}
                    >
                      ➕ Ajouter
                    </button>
                  ) : null}
                </div>
              );
            })()}
          </>
        ) : null}

        {section.type === "interface_desktop" ? (
          <>
            <PlainField
              label="Nom du logiciel"
              value={section.fields.nom_logiciel ?? ""}
              disabled={disabled}
              onChange={(v) => patch({ nom_logiciel: v })}
            />
            <PlainField
              label="Modules principaux (un par ligne)"
              value={section.fields.modules_principaux ?? ""}
              disabled={disabled}
              multiline
              onChange={(v) => patch({ modules_principaux: v })}
            />
            <PlainField
              label="Menu principal (un par ligne)"
              value={section.fields.menu_principal ?? ""}
              disabled={disabled}
              multiline
              onChange={(v) => patch({ menu_principal: v })}
            />
          </>
        ) : null}

        {section.type === "licence" ? (
          <>
            <FieldRow label="Type">
              <select
                value={section.fields.type_licence ?? "cf-one"}
                disabled={disabled}
                onChange={(e) => patch({ type_licence: e.target.value })}
                className={INPUT}
              >
                <option value="cf-one">CF-ONE (one shot)</option>
                <option value="cf-sub">CF-SUB (abonnement)</option>
              </select>
            </FieldRow>
            <PlainField
              label="Prix one shot"
              value={section.fields.prix_one_shot ?? ""}
              disabled={disabled}
              type="number"
              onChange={(v) => patch({ prix_one_shot: v })}
            />
            <PlainField
              label="Prix mensuel abonnement"
              value={section.fields.prix_mensuel ?? ""}
              disabled={disabled}
              type="number"
              onChange={(v) => patch({ prix_mensuel: v })}
            />
            <PlainField
              label="Fonctionnalités incluses"
              value={section.fields.fonctionnalites_incluses ?? ""}
              disabled={disabled}
              multiline
              onChange={(v) => patch({ fonctionnalites_incluses: v })}
            />
          </>
        ) : null}

        {section.type === "scene_video" ? (
          <>
            <TextField
              label="Description (FR)"
              fieldType="description"
              value={section.fields.description_fr ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI
                  ? patchAI({ description_fr: v })
                  : patch({ description_fr: v })
              }
              disabled={disabled}
              multiline
            />
            <FieldRow label="Durée (secondes)">
              <select
                value={section.fields.duree_secondes ?? "5"}
                disabled={disabled}
                onChange={(e) => patch({ duree_secondes: e.target.value })}
                className={INPUT}
              >
                <option value="5">5 s</option>
                <option value="10">10 s</option>
              </select>
            </FieldRow>
            <TextField
              label="Style"
              fieldType="description"
              value={section.fields.style ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI ? patchAI({ style: v }) : patch({ style: v })
              }
              disabled={disabled}
            />
          </>
        ) : null}

        {section.type === "musique_video" ? (
          <>
            <FieldRow label="Style musical">
              <select
                value={section.fields.style_musical ?? "Corporate"}
                disabled={disabled}
                onChange={(e) => patch({ style_musical: e.target.value })}
                className={INPUT}
              >
                <option value="Épique">Épique</option>
                <option value="Calme">Calme</option>
                <option value="Dynamique">Dynamique</option>
                <option value="Corporate">Corporate</option>
                <option value="Ambient">Ambient</option>
              </select>
            </FieldRow>
            <FieldRow label="BPM souhaité">
              <select
                value={section.fields.bpm ?? "Moyen"}
                disabled={disabled}
                onChange={(e) => patch({ bpm: e.target.value })}
                className={INPUT}
              >
                <option value="Lent">Lent</option>
                <option value="Moyen">Moyen</option>
                <option value="Rapide">Rapide</option>
              </select>
            </FieldRow>
            <TextField
              label="Description ambiance"
              fieldType="description"
              value={section.fields.ambiance ?? ""}
              context={context}
              onChange={(v, fromAI) =>
                fromAI ? patchAI({ ambiance: v }) : patch({ ambiance: v })
              }
              disabled={disabled}
            />
          </>
        ) : null}
      </div>

      <div className="mt-4 border-t border-[rgba(0,212,255,0.1)] pt-3">
        <p className="mb-2 text-[10px] uppercase tracking-wider text-cf-muted">
          Aperçu miniature
        </p>
        <div
          className={[
            "h-16 rounded border border-[rgba(0,212,255,0.1)] bg-[#0d0d14] p-2 text-[10px] text-cf-muted",
            section.animationClass,
          ].join(" ")}
        >
          {previewLabel}
        </div>
      </div>
    </div>
  );
}
