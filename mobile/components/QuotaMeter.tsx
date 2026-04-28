import { StyleSheet, Text, View } from "react-native";

export function QuotaMeter({ used, limit }: { used: number; limit: number }) {
  const pct = Math.min(100, (used / Math.max(1, limit)) * 100);
  return (
    <View style={styles.wrap}>
      <View style={styles.bar}><View style={[styles.fill, { width: `${pct}%` }]} /></View>
      <Text style={styles.label}>{used} / {limit} calls</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { padding: 12 },
  bar: { height: 8, backgroundColor: "#1a1a1a", borderRadius: 4, overflow: "hidden" },
  fill: { height: "100%", backgroundColor: "#6366f1" },
  label: { color: "#888", fontSize: 12, marginTop: 6 },
});
