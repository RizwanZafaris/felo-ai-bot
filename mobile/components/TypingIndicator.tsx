import { useEffect, useRef } from "react";
import { Animated, StyleSheet, View } from "react-native";

export function TypingIndicator() {
  const dots = [useRef(new Animated.Value(0.3)).current, useRef(new Animated.Value(0.3)).current, useRef(new Animated.Value(0.3)).current];
  useEffect(() => {
    const seq = dots.map((d, i) =>
      Animated.loop(Animated.sequence([
        Animated.delay(i * 150),
        Animated.timing(d, { toValue: 1, duration: 300, useNativeDriver: true }),
        Animated.timing(d, { toValue: 0.3, duration: 300, useNativeDriver: true }),
      ])),
    );
    seq.forEach((s) => s.start());
    return () => seq.forEach((s) => s.stop());
  }, []);
  return (
    <View style={styles.row}>
      {dots.map((d, i) => <Animated.View key={i} style={[styles.dot, { opacity: d }]} />)}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", padding: 16 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "#6366f1", marginHorizontal: 2 },
});
