import { useEffect, useState } from "react";
import * as Crypto from "expo-crypto";
import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "felo_session_id";

let _listeners: ((id: string) => void)[] = [];
let _current: string | null = null;

async function _load(): Promise<string> {
  if (_current) return _current;
  const existing = await AsyncStorage.getItem(KEY);
  if (existing) { _current = existing; return existing; }
  const fresh = Crypto.randomUUID();
  await AsyncStorage.setItem(KEY, fresh);
  _current = fresh;
  return fresh;
}

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(_current);

  useEffect(() => {
    let mounted = true;
    _load().then((id) => { if (mounted) setSessionId(id); });
    const sub = (id: string) => setSessionId(id);
    _listeners.push(sub);
    return () => {
      mounted = false;
      _listeners = _listeners.filter((l) => l !== sub);
    };
  }, []);

  const resetSession = async () => {
    const fresh = Crypto.randomUUID();
    await AsyncStorage.setItem(KEY, fresh);
    _current = fresh;
    _listeners.forEach((l) => l(fresh));
  };

  return { sessionId, resetSession };
}
