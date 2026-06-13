import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  FlatList,
  Linking,
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
import { fetchProjects, Project } from "../../lib/api";
import { colors, PROJECT_TYPE_LABELS, spacing } from "../../lib/theme";
import { formatRelativeDate } from "../../lib/utils";

const FILTERS = [
  { key: "all", label: "Tous" },
  { key: "vitrine_next", label: "Vitrine" },
  { key: "ecommerce", label: "E-commerce" },
  { key: "application_web", label: "App web" },
  { key: "extension_navigateur", label: "Extension" },
] as const;

export default function ProjectsScreen() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");

  const { data = [], isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const filtered = useMemo(() => {
    if (filter === "all") return data;
    return data.filter((p) => p.project_type === filter);
  }, [data, filter]);

  const renderItem = ({ item }: { item: Project }) => {
    const online = Boolean(item.demo_url);
    return (
      <GlassCard style={styles.card}>
        <View style={styles.rowBetween}>
          <Text style={styles.title}>{item.title}</Text>
          <Badge
            label={PROJECT_TYPE_LABELS[item.project_type] ?? item.project_type}
            variant="gold"
          />
        </View>
        <Text style={styles.muted}>{formatRelativeDate(item.created_at)}</Text>
        <View style={styles.footer}>
          <Badge
            label={online ? "En ligne" : "Hors ligne"}
            variant={online ? "teal" : "gray"}
          />
          {online ? (
            <Pressable
              onPress={() => Linking.openURL(item.demo_url!)}
              style={styles.linkBtn}
            >
              <Text style={styles.linkText}>Ouvrir →</Text>
            </Pressable>
          ) : null}
        </View>
      </GlassCard>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Text style={styles.header}>Projets</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filters}
      >
        {FILTERS.map((f) => (
          <Pressable
            key={f.key}
            onPress={() => setFilter(f.key)}
            style={[
              styles.filterPill,
              filter === f.key && styles.filterPillActive,
            ]}
          >
            <Text
              style={[
                styles.filterText,
                filter === f.key && styles.filterTextActive,
              ]}
            >
              {f.label}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={() => refetch()}
            tintColor={colors.gold}
          />
        }
        ListEmptyComponent={
          <GlassCard>
            <Text style={styles.muted}>
              {isLoading ? "Chargement…" : "Aucun projet"}
            </Text>
          </GlassCard>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    color: colors.gold,
    fontSize: 24,
    fontWeight: "700",
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  filters: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  filterPill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    marginRight: spacing.sm,
  },
  filterPillActive: {
    borderColor: colors.gold,
    backgroundColor: "#2a2418",
  },
  filterText: { color: colors.textSecondary, fontSize: 13 },
  filterTextActive: { color: colors.gold, fontWeight: "600" },
  list: { padding: spacing.md, gap: spacing.sm },
  card: { marginBottom: spacing.sm },
  rowBetween: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "600",
    flex: 1,
  },
  muted: { color: colors.textSecondary, fontSize: 13 },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: spacing.sm,
  },
  linkBtn: { padding: spacing.xs },
  linkText: { color: colors.gold, fontWeight: "600" },
});
