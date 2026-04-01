import { create } from "zustand";
import { API_URL } from "../api/apiURL";

interface SettingsState {
  app_title: string;
  navbar_color: string;
  instance_label: string;
  loaded: boolean;
  fetchSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  app_title: "CompIntel Monitor",
  navbar_color: "slate",
  instance_label: "DEV",
  loaded: false,
  fetchSettings: async () => {
    try {
      const res = await fetch(`${API_URL}/webapp_options`);
      if (res.ok) {
        const data: { name: string; value: string }[] = await res.json();
        const map: Record<string, string> = {};
        data.forEach((s) => (map[s.name] = s.value));
        set({
          app_title: map.app_title || "CompIntel Monitor",
          navbar_color: map.navbar_color || "slate",
          instance_label: map.instance_label || "",
          loaded: true,
        });
      }
    } catch {
      // Use defaults on error
    }
  },
}));
