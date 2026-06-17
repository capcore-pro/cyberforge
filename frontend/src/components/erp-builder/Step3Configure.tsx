import type { ErpProjectUpsert } from "@/lib/erp-builder-api";
import { Input } from "@/components/ui";

export function Step3Configure({
  value,
  onChange,
  disabled,
}: {
  value: ErpProjectUpsert;
  onChange: (next: ErpProjectUpsert) => void;
  disabled?: boolean;
}) {
  const port = value.port ?? 8069;
  const previewUrl = `http://localhost:${port}`;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Nom du projet
          </label>
          <Input
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
            disabled={disabled}
            placeholder="ERP Martin SARL"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Nom du client
          </label>
          <Input
            value={value.client_name}
            onChange={(e) => onChange({ ...value, client_name: e.target.value })}
            disabled={disabled}
            placeholder="Martin SARL"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Email administrateur
          </label>
          <Input
            type="email"
            value={value.admin_email}
            onChange={(e) => onChange({ ...value, admin_email: e.target.value })}
            disabled={disabled}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Mot de passe administrateur
          </label>
          <Input
            type="password"
            value={value.admin_password}
            onChange={(e) => onChange({ ...value, admin_password: e.target.value })}
            disabled={disabled}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
              Couleur principale
            </label>
            <input
              type="color"
              value={value.primary_color}
              onChange={(e) => onChange({ ...value, primary_color: e.target.value })}
              disabled={disabled}
              className="h-10 w-full cursor-pointer rounded border border-white/10 bg-transparent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
              Port d&apos;accès
            </label>
            <Input
              type="number"
              value={String(port)}
              onChange={(e) =>
                onChange({ ...value, port: Number(e.target.value) || null })
              }
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      <div className="rounded-card border border-violet-500/20 bg-violet-500/5 p-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-violet-300">
          Aperçu URL finale
        </p>
        <p className="mt-3 break-all font-mono text-lg text-cyan-300">{previewUrl}</p>
        <p className="mt-4 text-sm text-cf-muted">
          Une fois l&apos;installation terminée, vous accéderez à votre ERP à cette adresse
          depuis ce poste (Docker local).
        </p>
        <div
          className="mt-4 h-2 rounded-full"
          style={{ backgroundColor: value.primary_color }}
        />
      </div>
    </div>
  );
}
