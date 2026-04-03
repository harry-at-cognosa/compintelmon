import { create } from "zustand";
import { API_URL } from "../api/apiURL";
import getColor from "../api/getColor";

interface SettingsState {
  app_title: string;
  navbar_color: string;
  instance_label: string;
  loaded: boolean;
  fetchSettings: () => Promise<void>;
}

function applyThemeColors(colorName: string) {
  const root = document.documentElement;
  const shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900];
  shades.forEach((shade) => {
    root.style.setProperty(`--theme-color-${shade}`, getColor(colorName, shade));
  });
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
        const color = map.navbar_color || "slate";
        applyThemeColors(color);
        set({
          app_title: map.app_title || "CompIntel Monitor",
          navbar_color: color,
          instance_label: map.instance_label || "",
          loaded: true,
        });
      }
    } catch {
      applyThemeColors("slate");
    }
  },
}));
