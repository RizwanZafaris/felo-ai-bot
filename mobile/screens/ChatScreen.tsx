import { useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { MessageBubble } from "../components/MessageBubble";
import { TypingIndicator } from "../components/TypingIndicator";
import { useChat } from "../hooks/useChat";
import { useSession } from "../hooks/useSession";

export default function ChatScreen({ provider, model, userId }: { provider: string; model: string; userId: string }) {
  const { sessionId } = useSession();
  const { messages, send, loading } = useChat(sessionId, userId, provider, model);
  const [text, setText] = useState("");
  const listRef = useRef<FlatList>(null);

  const onSend = () => {
    if (!text.trim()) return;
    send(text.trim());
    setText("");
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 50);
  };

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <FlatList
        ref={listRef}
        style={styles.flex}
        data={messages}
        keyExtractor={(_, i) => String(i)}
        renderItem={({ item }) => <MessageBubble msg={item} />}
        ListFooterComponent={loading ? <TypingIndicator /> : null}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
      />
      <View style={styles.inputBar}>
        <TextInput
          value={text} onChangeText={setText}
          placeholder="Ask about your spending, savings, or goals…"
          placeholderTextColor="#666"
          multiline style={styles.input}
        />
        <Pressable onPress={onSend} style={styles.send}>
          <Text style={{ color: "#fff", fontWeight: "600" }}>Send</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#0f0f0f" },
  inputBar: { flexDirection: "row", padding: 12, borderTopWidth: 1, borderColor: "#222", backgroundColor: "#0f0f0f" },
  input: { flex: 1, backgroundColor: "#1a1a1a", color: "#e5e5e5", borderRadius: 8, padding: 10, maxHeight: 100 },
  send: { marginLeft: 8, paddingHorizontal: 16, justifyContent: "center", backgroundColor: "#6366f1", borderRadius: 8 },
});
