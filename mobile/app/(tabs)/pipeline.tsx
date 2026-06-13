import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { GlassCard } from "../../components/ui/GlassCard";
import {
  createProspect,
  fetchProspects,
  moveProspect,
  Prospect,
} from "../../lib/api";
import {
  colors,
  nextStatut,
  PROSPECT_STATUTS,
  spacing,
  STATUT_COLORS,
  STATUT_LABELS,
  ProspectStatut,
} from "../../lib/theme";

export default function PipelineScreen() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [nom, setNom] = useState("");
  const [entreprise, setEntreprise] = useState("");
  const [email, setEmail] = useState("");

  const { data = [] } = useQuery({
    queryKey: ["prospects"],
    queryFn: () => fetchProspects(),
  });

  const grouped = useMemo(() => {
    const map = Object.fromEntries(
      PROSPECT_STATUTS.map((s) => [s, [] as Prospect[]]),
    ) as Record<ProspectStatut, Prospect[]>;
    for (const prospect of data) {
      const key = (PROSPECT_STATUTS.includes(prospect.statut as ProspectStatut)
        ? prospect.statut
        : "nouveau") as ProspectStatut;
      map[key].push(prospect);
    }
    return map;
  }, [data]);

  const moveMutation = useMutation({
    mutationFn: ({ id, statut }: { id: string; statut: string }) =>
      moveProspect(id, statut),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prospects"] }),
    onError: (err: Error) => Alert.alert("Erreur", err.message),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createProspect({
        nom: nom.trim(),
        entreprise: entreprise.trim() || undefined,
        email: email.trim() || undefined,
      }),
    onSuccess: () => {
      setModalOpen(false);
      setNom("");
      setEntreprise("");
      setEmail("");
      queryClient.invalidateQueries({ queryKey: ["prospects"] });
    },
    onError: (err: Error) => Alert.alert("Erreur", err.message),
  });

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Text style={styles.header}>Pipeline</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.columns}
      >
        {PROSPECT_STATUTS.map((statut) => (
          <View key={statut} style={styles.column}>
            <View
              style={[
                styles.columnHeader,
                { borderColor: STATUT_COLORS[statut] },
              ]}
            >
              <Text style={[styles.columnTitle, { color: STATUT_COLORS[statut] }]}>
                {STATUT_LABELS[statut]}
              </Text>
              <Text style={styles.count}>{grouped[statut].length}</Text>
            </View>
            <ScrollView style={styles.columnBody}>
              {grouped[statut].map((prospect) => {
                const next = nextStatut(prospect.statut);
                return (
                  <GlassCard key={prospect.id} style={styles.card}>
                    <Text style={styles.name}>{prospect.nom}</Text>
                    {prospect.entreprise ? (
                      <Text style={styles.muted}>{prospect.entreprise}</Text>
                    ) : null}
                    {(prospect.valeur_estimee ?? 0) > 0 ? (
                      <Text style={styles.value}>
                        {prospect.valeur_estimee} €
                      </Text>
                    ) : null}
                    {next ? (
                      <Pressable
                        style={styles.advanceBtn}
                        onPress={() =>
                          moveMutation.mutate({ id: prospect.id, statut: next })
                        }
                      >
                        <Text style={styles.advanceText}>→</Text>
                      </Pressable>
                    ) : null}
                  </GlassCard>
                );
              })}
            </ScrollView>
          </View>
        ))}
      </ScrollView>

      <Pressable style={styles.fab} onPress={() => setModalOpen(true)}>
        <Text style={styles.fabText}>+</Text>
      </Pressable>

      <Modal visible={modalOpen} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <GlassCard style={styles.modalCard}>
            <Text style={styles.modalTitle}>Nouveau prospect</Text>
            <TextInput
              style={styles.input}
              placeholder="Nom *"
              placeholderTextColor={colors.textMuted}
              value={nom}
              onChangeText={setNom}
            />
            <TextInput
              style={styles.input}
              placeholder="Entreprise"
              placeholderTextColor={colors.textMuted}
              value={entreprise}
              onChangeText={setEntreprise}
            />
            <TextInput
              style={styles.input}
              placeholder="Email"
              placeholderTextColor={colors.textMuted}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <View style={styles.modalActions}>
              <Pressable onPress={() => setModalOpen(false)}>
                <Text style={styles.muted}>Annuler</Text>
              </Pressable>
              <Pressable
                onPress={() => createMutation.mutate()}
                disabled={!nom.trim()}
              >
                <Text style={styles.save}>Créer</Text>
              </Pressable>
            </View>
          </GlassCard>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    color: colors.gold,
    fontSize: 24,
    fontWeight: "700",
    padding: spacing.md,
  },
  columns: { paddingHorizontal: spacing.md, paddingBottom: spacing.xl },
  column: {
    width: 220,
    marginRight: spacing.md,
    maxHeight: "88%",
  },
  columnHeader: {
    borderWidth: 1,
    borderRadius: 8,
    padding: spacing.sm,
    marginBottom: spacing.sm,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  columnTitle: { fontWeight: "700", fontSize: 12 },
  count: { color: colors.textSecondary, fontWeight: "600" },
  columnBody: { flex: 1 },
  card: { marginBottom: spacing.sm },
  name: { color: colors.textPrimary, fontWeight: "600", fontSize: 15 },
  muted: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  value: { color: colors.gold, marginTop: spacing.xs, fontWeight: "600" },
  advanceBtn: {
    alignSelf: "flex-end",
    marginTop: spacing.sm,
    backgroundColor: colors.cardSecondary,
    borderRadius: 8,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  advanceText: { color: colors.gold, fontSize: 18, fontWeight: "700" },
  fab: {
    position: "absolute",
    right: spacing.lg,
    bottom: spacing.lg,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.gold,
    alignItems: "center",
    justifyContent: "center",
  },
  fabText: { color: colors.bg, fontSize: 28, fontWeight: "700" },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "flex-end",
  },
  modalCard: { borderRadius: 0, borderWidth: 0, padding: spacing.lg },
  modalTitle: {
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: "700",
    marginBottom: spacing.md,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: spacing.sm,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
    backgroundColor: colors.cardSecondary,
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: spacing.md,
  },
  save: { color: colors.gold, fontWeight: "700" },
});
