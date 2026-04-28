import { useEffect, useState } from "react";
import * as Crypto from "expo-crypto";
import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "felo_session_id";

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const existing = await AsyncStorage.getItem(KEY);
      if (existing) return setSessionId(existing);
      const fresh = Crypto.randomUUID();
      await AsyncStorage.setItem(KEY, fresh);
      setSessionId(fresh);
    })();
  }, []);

  const resetSession = async () => {
    const fresh = Crypto.randomUUID();
    await AsyncStorage.setItem(KEY, fresh);
    setSessionId(fresh);
  };

  return { sessionId, resetSession };
}
