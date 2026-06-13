import { useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Badge } from "../../components/ui/Badge";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatusDot } from "../../components/ui/StatusDot";
import {
  fetchAlerts,
  fetchAuditEvents,
  fetchDashboard,
} from "../../lib/api";
import { colors, spacing } from "../../lib/theme";
import {
  formatEuroFromUsd,
  formatPercent,
  formatRelativeDate,
} from "../../lib/utils";

export default function DashboardScreen() {
  const [refreshing, setRefreshing] = useState(false);

  const { data, isLoading, refetch, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      const [projects, agents, llm, supervisor, health] =
        await fetchDashboard();
      const [alerts, generations] = await Promise.all([
        fetchAlerts().catch(() => ({ items: [], count: 0 })),
        fetchAuditEvents("project_generated", 3).catch(() => ({
          items: [],
          count: 0,
        })),
      ]);
      return {
        projects,
        agents,
        llm,
        supervisor,
        health,
        alerts,
        generations,
      };
    },
  });

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const healthOk = !isError && data?.health?.api?.status === "online";
  const openAlerts = data?.alerts?.count ?? 0;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.gold}
          />
        }
      >
        <View style={styles.header}>
          <Text style={styles.title}>CyberForge</Text>
          <View style={styles.statusRow}>
            <StatusDot status={healthOk ? "online" : "error"} />
            <Text style={styles.statusText}>
              {isLoading
                ? "Connexion…"
                : healthOk
                  ? "Backend en ligne"
                  : "Backend hors ligne"}
            </Text>
          </View>
        </View>

        <GlassCard style={styles.section}>
          <Text style={styles.sectionTitle}>Agents</Text>
          <Badge
            label={`${data?.agents?.active_count ?? 0}/${data?.agents?.total_agents ?? 11} agents actifs`}
            variant="gold"
          />
        </GlassCard>

        <Text style={styles.sectionTitle}>Pipeline</Text>
        <View style={styles.kpiGrid}>
          <GlassCard style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Coût LLM ce mois</Text>
            <Text style={styles.kpiValue}>
              {formatEuroFromUsd(data?.llm?.monthly?.total_cost_usd)}
            </Text>
          </GlassCard>
          <GlassCard style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Pass rate validation</Text>
            <Text style={styles.kpiValue}>
              {formatPercent(data?.supervisor?.pass_rate)}
            </Text>
          </GlassCard>
          <GlassCard style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Projets générés</Text>
            <Text style={styles.kpiValue}>
              {data?.projects?.length ?? 0}
            </Text>
          </GlassCard>
          <GlassCard style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Alertes ouvertes</Text>
            <Text
              style={[
                styles.kpiValue,
                openAlerts > 0 && { color: colors.error },
              ]}
            >
              {openAlerts}
            </Text>
          </GlassCard>
        </View>

        <Text style={styles.sectionTitle}>Dernières générations</Text>
        {(data?.generations?.items ?? []).length === 0 ? (
          <GlassCard>
            <Text style={styles.muted}>Aucune génération récente</Text>
          </GlassCard>
        ) : (
          (data?.generations?.items ?? []).map((event) => {
            const payload = event.payload ?? {};
            return (
              <GlassCard key={event.id} style={styles.listItem}>
                <View style={styles.rowBetween}>
                  <Badge
                    label={String(payload.project_type ?? "projet")}
                    variant="teal"
                  />
                  <Text style={styles.muted}>
                    {formatRelativeDate(event.created_at)}
                  </Text>
                </View>
                <Text style={styles.itemTitle}>
                  {String(payload.client_name ?? "Client")}
                </Text>
                <Text style={styles.muted}>
                  {payload.duration_ms
                    ? `${payload.duration_ms} ms`
                    : "—"}{" "}
                  ·{" "}
                  {payload.cost_usd
                    ? formatEuroFromUsd(Number(payload.cost_usd))
                    : "—"}
                </Text>
              </GlassCard>
            );
          })
        )}

        <Text style={styles.sectionTitle}>Alertes ouvertes</Text>
        {openAlerts === 0 ? (
          <GlassCard>
            <Text style={styles.ok}>✓ Système opérationnel</Text>
          </GlassCard>
        ) : (
          (data?.alerts?.items ?? []).slice(0, 5).map((alert) => (
            <GlassCard key={alert.id} style={styles.listItem}>
              <View style={styles.rowBetween}>
                <Badge
                  label={alert.severity ?? "info"}
                  variant={
                    alert.severity === "critical"
                      ? "red"
                      : alert.severity === "warning"
                        ? "amber"
                        : "gray"
                  }
                />
                <Text style={styles.muted}>
                  {formatRelativeDate(alert.created_at)}
                </Text>
              </View>
              <Text style={styles.itemTitle}>
                {alert.title ?? alert.message ?? "Alerte"}
              </Text>
            </GlassCard>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, gap: spacing.sm, paddingBottom: spacing.xl },
  header: { marginBottom: spacing.sm },
  title: {
    color: colors.gold,
    fontSize: 28,
    fontWeight: "700",
  },
  statusRow: { flexDirection: "row", alignItems: "center", marginTop: spacing.xs },
  statusText: { color: colors.textSecondary, fontSize: 14 },
  section: { marginBottom: spacing.sm },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "600",
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  kpiCard: { width: "48%", minWidth: 150 },
  kpiLabel: { color: colors.textSecondary, fontSize: 12, marginBottom: spacing.xs },
  kpiValue: { color: colors.textPrimary, fontSize: 20, fontWeight: "700" },
  listItem: { marginBottom: spacing.sm },
  rowBetween: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.xs,
  },
  itemTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: "600" },
  muted: { color: colors.textSecondary, fontSize: 13 },
  ok: { color: colors.success, fontSize: 15, fontWeight: "600" },
});
