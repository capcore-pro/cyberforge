import { Badge, Card } from "@/components/ui";
import type { Workflow } from "@/lib/workflows-api";

const PROJECT_TYPE_LABELS: Record<string, string> = {
  vitrine_next: "Vitrine",
  ecommerce: "E-commerce",
  site_reservation: "Réservation",
  application_web: "App web",
  crm: "CRM",
  real_app: "App React",
  extension_navigateur: "Extension",
};

const PROJECT_TYPE_VARIANTS: Record<
  string,
  "gold" | "teal" | "amber" | "blue" | "gray"
> = {
  vitrine_next: "gold",
  ecommerce: "teal",
  site_reservation: "amber",
  application_web: "blue",
  crm: "blue",
  real_app: "blue",
  extension_navigateur: "gray",
};

interface WorkflowCardProps {
  workflow: Workflow;
  onOpen: (workflow: Workflow) => void;
}

export function WorkflowCard({ workflow, onOpen }: WorkflowCardProps) {
  return (
    <Card
      hoverable
      padding="md"
      onClick={() => onOpen(workflow)}
      className="text-left"
    >
      <div className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-white">{workflow.name}</h3>
          <Badge variant="gold" size="sm">
            {workflow.workflow_type}
          </Badge>
        </div>

        {workflow.description ? (
          <p className="line-clamp-2 text-xs text-white/45">{workflow.description}</p>
        ) : null}

        <p className="text-xs text-white/50">
          {workflow.step_count} steps · v{workflow.version}
        </p>

        <div className="flex flex-wrap gap-1.5">
          {workflow.project_types.map((type) => (
            <Badge
              key={type}
              variant={PROJECT_TYPE_VARIANTS[type] ?? "gray"}
              size="sm"
            >
              {PROJECT_TYPE_LABELS[type] ?? type}
            </Badge>
          ))}
        </div>

        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onOpen(workflow);
          }}
          className="text-xs font-medium text-cf-gold transition hover:text-white"
        >
          Voir le graphe →
        </button>
      </div>
    </Card>
  );
}
