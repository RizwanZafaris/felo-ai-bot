import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Picker } from "@react-native-picker/picker";
import { QuotaMeter } from "../components/QuotaMeter";
import { clearSession, getModels, getQuota } from "../api/coach";
import { useSession } from "../hooks/useSession";

type Props = {
  userId: string;
  provider: string; setProvider: (s: string) => void;
  model: string; setModel: (s: string) => void;
};

export default function SettingsScreen({ userId, provider, setProvider, model, setModel }: Props) {
  const { sessionId, resetSession } = useSession();
  const [models, setModels] = useState<{ provider: string; model: string }[]>([]);
  const [quota, setQuota] = useState({ used: 0, limit: 30, tier: "free" });

  useEffect(() => {
    getModels().then((d) => setModels(d.models)).catch(() => {});
    getQuota(userId).then(setQuota).catch(() => {});
  }, [userId]);

  const providers = [...new Set(models.map((m) => m.provider))];
  const filtered = models.filter((m) => m.provider === provider);

  return (
    <View style={styles.container}>
      <Text style={styles.h}>Settings</Text>

      <Text style={styles.tier}>Tier: {quota.tier.toUpperCase()}</Text>
      <QuotaMeter used={quota.used} limit={quota.limit} />

      <Text style={styles.label}>Provider</Text>
      <Picker selectedValue={provider} onValueChange={(v) => setProvider(String(v))} style={styles.picker} dropdownIconColor="#e5e5e5">
        {providers.map((p) => <Picker.Item key={p} label={p} value={p} color="#e5e5e5" />)}
      </Picker>

      <Text style={styles.label}>Model</Text>
      <Picker selectedValue={model} onValueChange={(v) => setModel(String(v))} style={styles.picker} dropdownIconColor="#e5e5e5">
        {filtered.map((m) => <Picker.Item key={m.model} label={m.model} value={m.model} color="#e5e5e5" />)}
      </Picker>

      <Pressable
        style={styles.button}
        onPress={async () => { if (sessionId) await clearSession(sessionId); await resetSession(); }}
      >
        <Text style={{ color: "#fff" }}>Clear conversation</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f0f0f", padding: 16 },
  h: { color: "#6366f1", fontSize: 20, fontWeight: "600", marginBottom: 16 },
  tier: { color: "#e5e5e5", marginBottom: 8 },
  label: { color: "#888", marginTop: 16, marginBottom: 4 },
  picker: { backgroundColor: "#1a1a1a", color: "#e5e5e5" },
  button: { marginTop: 24, backgroundColor: "#6366f1", padding: 12, borderRadius: 8, alignItems: "center" },
});
