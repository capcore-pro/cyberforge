import { useEffect, useRef } from "react";
import { Animated, StyleSheet, View } from "react-native";

import { colors } from "../../lib/theme";

type StatusDotProps = {
  status: "online" | "offline" | "running" | "warning" | "error";
  size?: number;
};

const STATUS_COLORS: Record<StatusDotProps["status"], string> = {
  online: colors.success,
  offline: colors.textMuted,
  running: colors.info,
  warning: colors.warning,
  error: colors.error,
};

export function StatusDot({ status, size = 10 }: StatusDotProps) {
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (status !== "running") return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 0.35,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: 700,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse, status]);

  return (
    <Animated.View
      style={[
        styles.dot,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: STATUS_COLORS[status],
          opacity: status === "running" ? pulse : 1,
        },
      ]}
    />
  );
}

const styles = StyleSheet.create({
  dot: {
    marginRight: 6,
  },
});
