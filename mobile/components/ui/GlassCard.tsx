import { ReactNode } from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import { colors, radius, spacing } from "../../lib/theme";

type GlassCardProps = {
  children: ReactNode;
  padding?: number;
  style?: StyleProp<ViewStyle>;
};

export function GlassCard({
  children,
  padding = spacing.md,
  style,
}: GlassCardProps) {
  return (
    <View style={[styles.card, { padding }, style]}>{children}</View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
  },
});
