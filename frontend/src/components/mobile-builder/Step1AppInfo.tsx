import type { MobileAppUpsert } from "@/lib/mobile-builder-api";
import { MOBILE_SECTORS } from "@/lib/mobile-builder-api";
import { Input } from "@/components/ui";

export function Step1AppInfo({
  value,
  onChange,
  disabled,
}: {
  value: MobileAppUpsert;
  onChange: (next: MobileAppUpsert) => void;
  disabled?: boolean;
}) {
  function patch(partial: Partial<MobileAppUpsert>) {
    onChange({ ...value, ...partial });
  }

  function slugify(text: string): string {
    return text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 40);
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
          Nom de l&apos;app
        </label>
        <Input
          value={value.name}
          onChange={(e) => {
            const name = e.target.value;
            patch({
              name,
              app_slug: value.app_slug || slugify(name),
              bundle_id:
                value.bundle_id ||
                `com.capcore.${slugify(name).replace(/-/g, "")}`,
            });
          }}
          disabled={disabled}
          placeholder="Resto Martin"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
          Description
        </label>
        <textarea
          className="cyber-prompt-field min-h-[80px] w-full resize-y"
          value={value.description}
          onChange={(e) => patch({ description: e.target.value })}
          disabled={disabled}
          placeholder="Application mobile pour..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Mode
          </label>
          <select
            className="cyber-input w-full"
            value={value.mode}
            onChange={(e) =>
              patch({ mode: e.target.value as MobileAppUpsert["mode"] })
            }
            disabled={disabled}
          >
            <option value="client">Client (APK unique)</option>
            <option value="product">Produit SaaS</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Secteur
          </label>
          <select
            className="cyber-input w-full"
            value={value.sector}
            onChange={(e) =>
              patch({ sector: e.target.value as MobileAppUpsert["sector"] })
            }
            disabled={disabled}
          >
            {MOBILE_SECTORS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Slug (identifiant unique)
          </label>
          <Input
            value={value.app_slug}
            onChange={(e) => patch({ app_slug: slugify(e.target.value) })}
            disabled={disabled}
            placeholder="resto-martin"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Bundle ID
          </label>
          <Input
            value={value.bundle_id}
            onChange={(e) => patch({ bundle_id: e.target.value })}
            disabled={disabled}
            placeholder="com.capcore.restomartin"
          />
        </div>
      </div>
    </div>
  );
}
