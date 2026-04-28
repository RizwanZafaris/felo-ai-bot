import { StyleSheet, Text, View } from "react-native";
import type { Msg } from "../hooks/useChat";
import { SourceCard } from "./SourceCard";

export function MessageBubble({ msg }: { msg: Msg }) {
  const isUser = msg.role === "user";
  return (
    <View style={[styles.row, isUser ? styles.right : styles.left]}>
      <View style={[styles.bubble, isUser ? styles.user : styles.ai, msg.refusal && styles.refusal]}>
        <Text style={[styles.text, isUser && { color: "#fff" }]}>{msg.text}</Text>
        {msg.sources && msg.sources.length > 0 && <SourceCard sources={msg.sources} />}
        {msg.refusal && <Text style={styles.badge}>Guardrail</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", marginVertical: 4, paddingHorizontal: 12 },
  left: { justifyContent: "flex-start" },
  right: { justifyContent: "flex-end" },
  bubble: { maxWidth: "85%", padding: 12, borderRadius: 12 },
  user: { backgroundColor: "#6366f1" },
  ai: { backgroundColor: "#1a1a1a", borderWidth: 1, borderColor: "#2a2a2a" },
  refusal: { borderColor: "#f59e0b" },
  text: { color: "#e5e5e5", lineHeight: 20 },
  badge: { color: "#f59e0b", fontSize: 10, marginTop: 6 },
});
