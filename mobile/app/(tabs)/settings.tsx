import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { GlassCard } from "../../components/ui/GlassCard";
import {
  DEFAULT_BASE_URL,
  fetchMobileHealth,
  normalizeBaseUrl,
  registerPushToken,
  testBackendConnection,
} from "../../lib/api";
import { useAppStore } from "../../lib/store";
import { colors, spacing } from "../../lib/theme";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const PUSH_UNAVAILABLE_MESSAGE =
  "Notifications push disponibles dans une prochaine version. Le backend envoie déjà des emails via Brevo.";

type PushPermissionResult =
  | { status: "granted"; token: string }
  | { status: "denied" }
  | { status: "unavailable" };

async function requestPushPermissions(): Promise<PushPermissionResult> {
  if (!Device.isDevice) {
    return { status: "unavailable" };
  }
  const { status: existing } = await Notifications.getPermissionsAsync();
  let finalStatus = existing;
  if (existing !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }
  if (finalStatus !== "granted") {
    return { status: "denied" };
  }
  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    return { status: "granted", token: tokenData.data };
  } catch {
    return { status: "unavailable" };
  }
}

export default function SettingsScreen() {
  const baseUrl = useAppStore((s) => s.baseUrl);
  const setBaseUrl = useAppStore((s) => s.setBaseUrl);
  const pushEnabled = useAppStore((s) => s.pushEnabled);
  const setPushEnabled = useAppStore((s) => s.setPushEnabled);
  const setPushToken = useAppStore((s) => s.setPushToken);

  const [urlInput, setUrlInput] = useState(baseUrl);
  const [testStatus, setTestStatus] = useState<string | null>(null);
  const [pushNotice, setPushNotice] = useState<string | null>(null);

  const testConnection = async () => {
    const normalizedUrl = normalizeBaseUrl(urlInput);
    setBaseUrl(normalizedUrl);
    setUrlInput(normalizedUrl);
    try {
      await testBackendConnection(normalizedUrl);
      setTestStatus("Connexion OK");
    } catch {
      setTestStatus("Erreur de connexion");
    }
  };

  const togglePush = async (enabled: boolean) => {
    if (!enabled) {
      setPushEnabled(false);
      setPushToken(null);
      setPushNotice(null);
      return;
    }
    setPushNotice(null);
    try {
      const result = await requestPushPermissions();
      if (result.status === "denied") {
        setPushEnabled(false);
        setPushToken(null);
        return;
      }
      if (result.status === "unavailable") {
        setPushEnabled(false);
        setPushToken(null);
        setPushNotice(PUSH_UNAVAILABLE_MESSAGE);
        return;
      }
      setPushToken(result.token);
      setPushEnabled(true);
      await registerPushToken(result.token, "android");
      const health = await fetchMobileHealth();
      Alert.alert(
        "Notifications",
        `Token enregistré (${health.tokens} appareil(s))`,
      );
    } catch {
      setPushEnabled(false);
      setPushToken(null);
      setPushNotice(PUSH_UNAVAILABLE_MESSAGE);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.header}>Paramètres</Text>

        <GlassCard>
          <Text style={styles.sectionTitle}>Connexion</Text>
          <Text style={styles.label}>URL du backend</Text>
          <TextInput
            style={styles.input}
            value={urlInput}
            onChangeText={setUrlInput}
            placeholder={DEFAULT_BASE_URL}
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
          />
          <Pressable style={styles.btn} onPress={testConnection}>
            <Text style={styles.btnText}>Tester la connexion</Text>
          </Pressable>
          {testStatus ? (
            <Text
              style={[
                styles.feedback,
                {
                  color: testStatus.includes("OK")
                    ? colors.success
                    : colors.error,
                },
              ]}
            >
              {testStatus}
            </Text>
          ) : null}
        </GlassCard>

        <GlassCard>
          <Text style={styles.sectionTitle}>Notifications</Text>
          <View style={styles.switchRow}>
            <Text style={styles.label}>Notifications push</Text>
            <Switch
              value={pushEnabled}
              onValueChange={togglePush}
              trackColor={{ false: colors.border, true: colors.gold }}
            />
          </View>
          {pushNotice ? (
            <Text style={styles.pushNotice}>{pushNotice}</Text>
          ) : null}
        </GlassCard>

        <GlassCard>
          <Text style={styles.sectionTitle}>À propos</Text>
          <Text style={styles.aboutLine}>Version app : 1.0.0</Text>
          <Text style={styles.aboutLine}>Backend : {baseUrl}</Text>
          <Text style={styles.aboutLine}>Développé par CapCore</Text>
        </GlassCard>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, gap: spacing.md, paddingBottom: spacing.xl },
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
  label: { color: colors.textSecondary, marginBottom: spacing.xs },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: spacing.sm,
    color: colors.textPrimary,
    backgroundColor: colors.cardSecondary,
    marginBottom: spacing.sm,
  },
  btn: {
    backgroundColor: colors.gold,
    borderRadius: 8,
    padding: spacing.sm,
    alignItems: "center",
  },
  btnText: { color: colors.bg, fontWeight: "700" },
  feedback: { marginTop: spacing.sm, fontSize: 13 },
  switchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  pushNotice: {
    marginTop: spacing.sm,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  aboutLine: { color: colors.textSecondary, marginBottom: spacing.xs },
});
