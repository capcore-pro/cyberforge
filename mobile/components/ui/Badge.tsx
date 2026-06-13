import { StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../../lib/theme";

type BadgeVariant = "gold" | "teal" | "amber" | "red" | "gray" | "info" | "purple";

const VARIANT_STYLES: Record<
  BadgeVariant,
  { bg: string; text: string; border: string }
> = {
  gold: { bg: "#2a2418", text: colors.gold, border: "#4a3f22" },
  teal: { bg: "#0f2a22", text: colors.teal, border: "#1f4a3a" },
  amber: { bg: "#2a2010", text: colors.warning, border: "#4a3818" },
  red: { bg: "#2a1414", text: colors.error, border: "#4a2222" },
  gray: { bg: colors.cardSecondary, text: colors.textSecondary, border: colors.border },
  info: { bg: "#142030", text: colors.info, border: "#243850" },
  purple: { bg: "#1f1430", text: colors.purple, border: "#352250" },
};

type BadgeProps = {
  label: string;
  variant?: BadgeVariant;
};

export function Badge({ label, variant = "gray" }: BadgeProps) {
  const palette = VARIANT_STYLES[variant];
  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: palette.bg,
          borderColor: palette.border,
        },
      ]}
    >
      <Text style={[styles.text, { color: palette.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: "flex-start",
    borderRadius: radius.full,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  text: {
    fontSize: 12,
    fontWeight: "600",
  },
});
