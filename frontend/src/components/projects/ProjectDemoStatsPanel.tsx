import { useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchDemoStats,
  type DemoTrackingStats,
} from "@/lib/demo-tracking-api";

export interface ProjectDemoStatsPanelProps {
  project_id: string;
}

function GlassCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-card border border-white/10 bg-white/5 p-4 shadow-[0_1px_0_rgba(255,255,255,0.04)_inset] backdrop-blur-xl">
      <div className="mb-4 flex items-center gap-2">
        <span
          className="inline-flex h-7 w-7 items-center justify-center rounded-control border border-white/10 bg-white/5 text-sm text-cf-gold"
          aria-hidden
        >
          <i className={`ti ${icon}`} />
        </span>
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
          {title}
        </h2>
      </div>
      {children}
    </div>
  );
}

function formatLastViewed(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function devicePercent(count: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((count / total) * 100);
}

function DeviceBar({
  emoji,
  label,
  count,
  total,
}: {
  emoji: string;
  label: string;
  count: number;
  total: number;
}) {
  const pct = devicePercent(count, total);
  const blocks = 6;
  const filled = total > 0 ? Math.max(1, Math.round((count / total) * blocks)) : 0;
  const bar = "█".repeat(filled) + "░".repeat(blocks - filled);

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-28 shrink-0 text-cf-muted">
        {emoji} {label}
      </span>
      <span className="font-mono text-xs tracking-wider text-cf-gold/80">{bar}</span>
      <span className="shrink-0 text-xs text-cf-label">{pct}%</span>
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Chargement statistiques démo">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="h-14 animate-pulse rounded-card bg-white/5" />
        <div className="h-14 animate-pulse rounded-card bg-white/5" />
        <div className="h-14 animate-pulse rounded-card bg-white/5" />
      </div>
      <div className="h-20 animate-pulse rounded-card bg-white/5" />
    </div>
  );
}

function KpiPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-cf-border-input bg-cf-secondary/40 px-4 py-3 text-center">
      <p className="text-lg font-semibold text-cf-text">{value}</p>
      <p className="mt-1 text-[10px] font-medium uppercase tracking-wider text-cf-label">
        {label}
      </p>
    </div>
  );
}

export function ProjectDemoStatsPanel({ project_id }: ProjectDemoStatsPanelProps) {
  const [stats, setStats] = useState<DemoTrackingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    void fetchDemoStats(project_id)
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err) => {
        if (!cancelled) setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [project_id]);

  if (loading) {
    return (
      <GlassCard title="Statistiques démo" icon="ti-eye">
        <StatsSkeleton />
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard title="Statistiques démo" icon="ti-eye">
        <p className="text-sm text-red-300">{error}</p>
      </GlassCard>
    );
  }

  const data = stats ?? {
    total_views: 0,
    unique_ips: 0,
    by_device: { mobile: 0, tablet: 0, desktop: 0 },
    last_viewed_at: null,
    views_this_week: 0,
    views_this_month: 0,
  };

  const totalDevice =
    data.by_device.mobile + data.by_device.tablet + data.by_device.desktop;

  return (
    <GlassCard title="Statistiques démo" icon="ti-eye">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <KpiPill label="vues" value={String(data.total_views)} />
          <KpiPill label="visiteurs uniques" value={String(data.unique_ips)} />
          <KpiPill
            label="dernière visite"
            value={formatLastViewed(data.last_viewed_at)}
          />
        </div>

        <div className="space-y-2 rounded-card border border-cf-border-input bg-cf-secondary/30 p-4">
          <DeviceBar
            emoji="📱"
            label="Mobile"
            count={data.by_device.mobile}
            total={totalDevice}
          />
          <DeviceBar
            emoji="💻"
            label="Desktop"
            count={data.by_device.desktop}
            total={totalDevice}
          />
          <DeviceBar
            emoji="📱"
            label="Tablette"
            count={data.by_device.tablet}
            total={totalDevice}
          />
        </div>

        <div className="flex flex-wrap gap-4 text-sm text-cf-muted">
          <span>
            Vues cette semaine :{" "}
            <strong className="text-cf-text">{data.views_this_week}</strong>
          </span>
          <span>
            Vues ce mois :{" "}
            <strong className="text-cf-text">{data.views_this_month}</strong>
          </span>
        </div>
      </div>
    </GlassCard>
  );
}

export function LazyProjectDemoStatsPanel(props: ProjectDemoStatsPanelProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = rootRef.current;
    if (!node) return;

    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={rootRef} className="min-h-[1px]">
      {visible ? (
        <ProjectDemoStatsPanel {...props} />
      ) : (
        <div
          className="h-24 rounded-card border border-cf-border-input bg-cf-card/40"
          aria-hidden
        />
      )}
    </div>
  );
}
