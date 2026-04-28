import { useState } from "react";
import { SafeAreaView, StatusBar, StyleSheet, Pressable, Text, View } from "react-native";
import ChatScreen from "./screens/ChatScreen";
import SettingsScreen from "./screens/SettingsScreen";

export default function App() {
  const [tab, setTab] = useState<"chat" | "settings">("chat");
  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("claude-sonnet-4-6");
  const userId = "demo-user";

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="light-content" />
      <View style={styles.tabs}>
        <Pressable onPress={() => setTab("chat")} style={[styles.tab, tab === "chat" && styles.active]}>
          <Text style={styles.tabText}>Chat</Text>
        </Pressable>
        <Pressable onPress={() => setTab("settings")} style={[styles.tab, tab === "settings" && styles.active]}>
          <Text style={styles.tabText}>Settings</Text>
        </Pressable>
      </View>
      {tab === "chat"
        ? <ChatScreen provider={provider} model={model} userId={userId} />
        : <SettingsScreen userId={userId} provider={provider} setProvider={setProvider} model={model} setModel={setModel} />}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0f0f0f" },
  tabs: { flexDirection: "row", borderBottomWidth: 1, borderColor: "#222" },
  tab: { flex: 1, padding: 14, alignItems: "center" },
  active: { borderBottomWidth: 2, borderColor: "#6366f1" },
  tabText: { color: "#e5e5e5" },
});
