import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import {
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Badge } from "../../components/ui/Badge";
import { GlassCard } from "../../components/ui/GlassCard";
import {
  acknowledgeAlert,
  Alert as MonitoringAlert,
  fetchAlerts,
  fetchMonitoringHealth,
  runMonitoringCheck,
} from "../../lib/api";
import { colors, spacing } from "../../lib/theme";
import { formatPercent, formatRelativeDate } from "../../lib/utils";

export default function MonitoringScreen() {
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const { data: health, refetch: refetchHealth } = useQuery({
    queryKey: ["monitoring-health"],
    queryFn: fetchMonitoringHealth,
  });

  const { data: alerts, refetch: refetchAlerts } = useQuery({
    queryKey: ["monitoring-alerts"],
    queryFn: fetchAlerts,
  });

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refetchHealth(), refetchAlerts()]);
    setRefreshing(false);
  }, [refetchAlerts, refetchHealth]);

  const ackMutation = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["monitoring-alerts"] }),
    onError: (err: Error) => Alert.alert("Erreur", err.message),
  });

  const scanMutation = useMutation({
    mutationFn: runMonitoringCheck,
    onSuccess: () => {
      setScanMessage("Scan terminé");
      queryClient.invalidateQueries({ queryKey: ["monitoring-health"] });
      queryClient.invalidateQueries({ queryKey: ["monitoring-alerts"] });
      setTimeout(() => setScanMessage(null), 2500);
    },
    onError: (err: Error) => Alert.alert("Erreur", err.message),
  });

  const overall = health?.overall_status ?? "unknown";
  const overallVariant =
    overall === "healthy"
      ? "teal"
      : overall === "degraded"
        ? "amber"
        : "red";

  const renderAlert = ({ item }: { item: MonitoringAlert }) => (
    <GlassCard style={styles.alertCard}>
      <View style={styles.rowBetween}>
        <Badge
          label={item.severity ?? "info"}
          variant={
            item.severity === "critical"
              ? "red"
              : item.severity === "warning"
                ? "amber"
                : "gray"
          }
        />
        <Text style={styles.muted}>{formatRelativeDate(item.created_at)}</Text>
      </View>
      <Text style={styles.alertTitle}>
        {item.title ?? item.message ?? "Alerte"}
      </Text>
      {item.source ? (
        <Text style={styles.muted}>Source : {item.source}</Text>
      ) : null}
      <Pressable
        style={styles.ackBtn}
        onPress={() => ackMutation.mutate(item.id)}
      >
        <Text style={styles.ackText}>Acquitter</Text>
      </Pressable>
    </GlassCard>
  );

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
        <Text style={styles.header}>Monitoring</Text>

        <GlassCard>
          <Text style={styles.sectionTitle}>Santé système</Text>
          <Badge label={overall} variant={overallVariant} />
          <View style={styles.metrics}>
            <Metric
              label="API"
              value={health?.api?.status === "online" ? "OK" : "KO"}
            />
            <Metric
              label="Agents"
              value={`${health?.agents?.active ?? 0}/${health?.agents?.total ?? 0}`}
            />
            <Metric
              label="Pipeline"
              value={formatPercent(health?.pipeline?.pass_rate)}
            />
            <Metric
              label="Coûts"
              value={`$${(health?.costs?.month_usd ?? 0).toFixed(2)}`}
            />
          </View>
        </GlassCard>

        <View style={styles.rowBetween}>
          <Text style={styles.sectionTitle}>Alertes ouvertes</Text>
          <Pressable
            style={styles.scanBtn}
            onPress={() => scanMutation.mutate()}
          >
            <Text style={styles.scanText}>
              {scanMutation.isPending ? "Scan…" : "Lancer un scan"}
            </Text>
          </Pressable>
        </View>
        {scanMessage ? (
          <Text style={styles.toast}>{scanMessage}</Text>
        ) : null}

        <FlatList
          data={alerts?.items ?? []}
          keyExtractor={(item) => item.id}
          renderItem={renderAlert}
          scrollEnabled={false}
          ListEmptyComponent={
            <GlassCard>
              <Text style={styles.muted}>Aucune alerte ouverte</Text>
            </GlassCard>
          }
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, gap: spacing.sm, paddingBottom: spacing.xl },
  header: {
    color: colors.gold,
    fontSize: 24,
    fontWeight: "700",
    marginBottom: spacing.sm,
  },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "600",
    marginBottom: spacing.sm,
  },
  metrics: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    marginTop: spacing.md,
  },
  metric: { minWidth: "42%" },
  metricLabel: { color: colors.textSecondary, fontSize: 12 },
  metricValue: {
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: "700",
    marginTop: 2,
  },
  rowBetween: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: spacing.sm,
  },
  scanBtn: {
    borderWidth: 1,
    borderColor: colors.gold,
    borderRadius: 8,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  scanText: { color: colors.gold, fontWeight: "600", fontSize: 12 },
  toast: { color: colors.success, fontSize: 13, marginBottom: spacing.xs },
  alertCard: { marginBottom: spacing.sm },
  alertTitle: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: "600",
    marginVertical: spacing.xs,
  },
  muted: { color: colors.textSecondary, fontSize: 13 },
  ackBtn: {
    alignSelf: "flex-start",
    marginTop: spacing.sm,
    paddingVertical: spacing.xs,
  },
  ackText: { color: colors.gold, fontWeight: "600" },
});
