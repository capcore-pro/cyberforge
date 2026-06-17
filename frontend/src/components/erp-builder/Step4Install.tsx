import { Button } from "@/components/ui";

export interface InstallStep {
  id: string;
  label: string;
  status: "pending" | "active" | "done" | "error";
}

const DEFAULT_STEPS: InstallStep[] = [
  { id: "compose", label: "Configuration générée", status: "pending" },
  { id: "pull", label: "Téléchargement images Docker", status: "pending" },
  { id: "start", label: "Démarrage des services", status: "pending" },
  { id: "health", label: "Vérification santé", status: "pending" },
  { id: "done", label: "ERP en ligne !", status: "pending" },
];

export function Step4Install({
  installing,
  steps,
  installResult,
  onInstall,
  onOpen,
}: {
  installing: boolean;
  steps: InstallStep[];
  installResult: { url: string; admin_email: string; admin_password: string } | null;
  onInstall: () => void;
  onOpen: (url: string) => void;
}) {
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore
    }
  }

  return (
    <div className="space-y-6">
      <Button
        variant="primary"
        icon="ti ti-server"
        loading={installing}
        disabled={installing}
        onClick={onInstall}
      >
        Lancer l&apos;installation
      </Button>

      <div className="rounded-card border border-white/10 bg-[#0f1117]/60 p-4">
        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-cf-muted">
          Progression
        </p>
        <ul className="space-y-3">
          {(steps.length ? steps : DEFAULT_STEPS).map((step) => (
            <li key={step.id} className="flex items-center gap-3 text-sm">
              <span
                className={[
                  "flex h-6 w-6 items-center justify-center rounded-full text-xs",
                  step.status === "done"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : step.status === "active"
                      ? "bg-cyan-500/20 text-cyan-300 animate-pulse"
                      : step.status === "error"
                        ? "bg-red-500/20 text-red-300"
                        : "bg-white/5 text-cf-muted",
                ].join(" ")}
              >
                {step.status === "done" ? "✓" : step.status === "active" ? "⏳" : "○"}
              </span>
              <span className={step.status === "done" ? "text-white" : "text-cf-muted"}>
                {step.label}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {installResult ? (
        <div className="rounded-card border border-emerald-500/30 bg-emerald-500/10 p-5">
          <p className="mb-3 font-semibold text-emerald-200">Votre ERP est prêt !</p>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="text-cf-muted">URL</span>
              <button
                type="button"
                onClick={() => void copy(installResult.url)}
                className="font-mono text-cyan-300 hover:underline"
              >
                {installResult.url}
              </button>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-cf-muted">Login</span>
              <button
                type="button"
                onClick={() => void copy(installResult.admin_email)}
                className="text-white hover:underline"
              >
                {installResult.admin_email}
              </button>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-cf-muted">Mot de passe</span>
              <button
                type="button"
                onClick={() => void copy(installResult.admin_password)}
                className="text-white hover:underline"
              >
                •••••••• (copier)
              </button>
            </div>
          </div>
          <Button
            variant="success"
            className="mt-4"
            icon="ti ti-external-link"
            onClick={() => onOpen(installResult.url)}
          >
            Ouvrir l&apos;ERP
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export function mapInstallMessageToSteps(
  message: string,
  current: InstallStep[],
): InstallStep[] {
  const steps = current.length ? [...current] : DEFAULT_STEPS.map((s) => ({ ...s }));
  const lower = message.toLowerCase();
  if (lower.includes("docker-compose") || lower.includes("génération")) {
    steps[0] = { ...steps[0], status: "done" };
    steps[1] = { ...steps[1], status: "active" };
  }
  if (lower.includes("téléchargement") || lower.includes("pull") || lower.includes("image")) {
    steps[0] = { ...steps[0], status: "done" };
    steps[1] = { ...steps[1], status: "active" };
  }
  if (lower.includes("démarrage") || lower.includes("starting") || lower.includes("created")) {
    steps[1] = { ...steps[1], status: "done" };
    steps[2] = { ...steps[2], status: "active" };
  }
  if (lower.includes("vérification") || lower.includes("santé") || lower.includes("health")) {
    steps[2] = { ...steps[2], status: "done" };
    steps[3] = { ...steps[3], status: "active" };
  }
  if (lower.includes("en ligne") || lower.includes("terminée")) {
    steps.forEach((s, i) => {
      steps[i] = { ...s, status: "done" };
    });
  }
  return steps;
}
