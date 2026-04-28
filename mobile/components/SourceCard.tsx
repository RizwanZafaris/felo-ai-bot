import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

export function SourceCard({ sources }: { sources: { label: string; value: string }[] }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={{ marginTop: 8 }}>
      <Pressable onPress={() => setOpen(!open)}>
        <Text style={styles.toggle}>Sources ({sources.length}) {open ? "▾" : "▸"}</Text>
      </Pressable>
      {open && sources.map((s, i) => (
        <Text key={i} style={styles.src}>• {s.label}: {s.value}</Text>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  toggle: { color: "#888", fontSize: 12 },
  src: { color: "#aaa", fontSize: 12, marginTop: 2 },
});
