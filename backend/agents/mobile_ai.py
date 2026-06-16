"""
MobileAI — génère une app React Native Expo complète à partir d'un brief.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from tools.eas_builder import configure_eas, generate_app_structure

logger = logging.getLogger(__name__)

# Secteurs supportés et écrans associés
SECTOR_SCREENS: dict[str, list[dict[str, str]]] = {
    "restaurant": [
        {"id": "menu", "title": "Menu", "route": "menu"},
        {"id": "reservation", "title": "Réservation", "route": "reservation"},
        {"id": "commande", "title": "Commander", "route": "commande"},
    ],
    "artisan": [
        {"id": "devis", "title": "Devis", "route": "devis"},
        {"id": "planning", "title": "Planning", "route": "planning"},
        {"id": "clients", "title": "Clients", "route": "clients"},
        {"id": "interventions", "title": "Interventions", "route": "interventions"},
    ],
    "commerce": [
        {"id": "catalogue", "title": "Catalogue", "route": "catalogue"},
        {"id": "panier", "title": "Panier", "route": "panier"},
        {"id": "fidelite", "title": "Fidélité", "route": "fidelite"},
    ],
    "service": [
        {"id": "rdv", "title": "Prendre RDV", "route": "rdv"},
        {"id": "suivi", "title": "Suivi", "route": "suivi"},
        {"id": "messagerie", "title": "Messagerie", "route": "messagerie"},
    ],
    "vitrine": [
        {"id": "presentation", "title": "Présentation", "route": "presentation"},
        {"id": "contact", "title": "Contact", "route": "contact"},
        {"id": "galerie", "title": "Galerie", "route": "galerie"},
        {"id": "avis", "title": "Avis", "route": "avis"},
    ],
}

FEATURE_SCREENS: dict[str, dict[str, str]] = {
    "auth": {"id": "auth", "title": "Connexion", "route": "auth"},
    "push_notifications": {"id": "notifications", "title": "Notifications", "route": "notifications"},
    "geolocation": {"id": "carte", "title": "Carte", "route": "carte"},
    "camera": {"id": "camera", "title": "Caméra", "route": "camera"},
    "stripe_payment": {"id": "paiement", "title": "Paiement", "route": "paiement"},
    "calendar": {"id": "calendrier", "title": "Calendrier", "route": "calendrier"},
    "chat": {"id": "chat", "title": "Chat", "route": "chat"},
    "offline_mode": {"id": "offline", "title": "Hors ligne", "route": "offline"},
}

ALL_FEATURES = list(FEATURE_SCREENS.keys())
ALL_SECTORS = list(SECTOR_SCREENS.keys())


@dataclass
class MobileGenerationResult:
    """Résultat de la génération MobileAI."""

    app_id: str
    files: dict[str, str] = field(default_factory=dict)
    screens: list[dict[str, str]] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    build_root: str = ""


def _normalize_features(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x) in FEATURE_SCREENS]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if str(x) in FEATURE_SCREENS]
        except json.JSONDecodeError:
            pass
    return []


def _resolve_screens(sector: str, features: list[str]) -> list[dict[str, str]]:
    sector_key = sector if sector in SECTOR_SCREENS else "vitrine"
    screens = list(SECTOR_SCREENS[sector_key])
    home = {"id": "home", "title": "Accueil", "route": "index"}
    if not any(s["id"] == "home" for s in screens):
        screens.insert(0, home)
    for feat in features:
        meta = FEATURE_SCREENS.get(feat)
        if meta and not any(s["id"] == meta["id"] for s in screens):
            screens.append(meta)
    return screens


def _package_json(name: str, features: list[str]) -> str:
    deps: dict[str, str] = {
        "@react-native-async-storage/async-storage": "1.23.1",
        "@react-navigation/bottom-tabs": "^6.6.1",
        "@react-navigation/native": "^6.1.18",
        "expo": "~51.0.0",
        "expo-constants": "~16.0.0",
        "expo-linking": "~6.3.0",
        "expo-router": "~3.5.0",
        "expo-status-bar": "~1.12.1",
        "nativewind": "^2.0.11",
        "react": "18.2.0",
        "react-native": "0.74.5",
        "react-native-gesture-handler": "2.16.2",
        "react-native-safe-area-context": "4.10.5",
        "react-native-screens": "3.31.1",
        "zustand": "^5.0.0",
    }
    if "push_notifications" in features:
        deps["expo-notifications"] = "~0.28.0"
        deps["expo-device"] = "~6.0.0"
    if "geolocation" in features:
        deps["expo-location"] = "~17.0.0"
    if "camera" in features:
        deps["expo-camera"] = "~15.0.0"
    if "calendar" in features:
        deps["expo-calendar"] = "~13.0.0"
    if "stripe_payment" in features:
        deps["@stripe/stripe-react-native"] = "0.37.2"
    if "offline_mode" in features:
        deps["@react-native-community/netinfo"] = "11.3.1"

    pkg = {
        "name": name.lower().replace(" ", "-")[:40] or "mobile-app",
        "version": "1.0.0",
        "main": "expo-router/entry",
        "private": True,
        "scripts": {
            "start": "expo start",
            "android": "expo run:android",
        },
        "dependencies": deps,
        "devDependencies": {
            "@types/react": "~18.2.79",
            "tailwindcss": "3.3.2",
            "typescript": "~5.3.3",
        },
    }
    return json.dumps(pkg, indent=2, ensure_ascii=False)


def _theme_ts(primary: str, secondary: str) -> str:
    return f'''export const theme = {{
  primary: "{primary}",
  secondary: "{secondary}",
  bg: "#0f1117",
  card: "#1a1d27",
  border: "#2a2f3d",
  text: "#f0f0f0",
  muted: "#9ca3af",
}};
'''


def _tailwind_config() -> str:
    return """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
"""


def _babel_config() -> str:
    return """module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: ["nativewind/babel"],
  };
};
"""


def _tsconfig() -> str:
    return json.dumps(
        {
            "extends": "expo/tsconfig.base",
            "compilerOptions": {"strict": True, "paths": {"@/*": ["./*"]}},
        },
        indent=2,
    )


def _global_css() -> str:
    return "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"


def _root_layout() -> str:
    return '''import "../global.css";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { theme } from "../lib/theme";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: theme.bg }}>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
      </Stack>
    </GestureHandlerRootView>
  );
}
'''


def _tabs_layout(screens: list[dict[str, str]], primary: str) -> str:
    tab_routes = [s for s in screens if s["route"] != "auth"][:5]
    screen_lines = "\n".join(
        f'        <Tabs.Screen name="{s["route"]}" options={{ title: "{s["title"]}" }} />'
        for s in tab_routes
    )
    return f'''import {{ Tabs }} from "expo-router";
import {{ theme }} from "../../lib/theme";

export default function TabLayout() {{
  return (
    <Tabs
      screenOptions={{{{
        headerShown: false,
        tabBarStyle: {{ backgroundColor: theme.card, borderTopColor: theme.border }},
        tabBarActiveTintColor: "{primary}",
        tabBarInactiveTintColor: theme.muted,
      }}}}
    >
{screen_lines}
    </Tabs>
  );
}}
'''


def _home_screen(app_name: str, sector: str, primary: str) -> str:
    return f'''import {{ View, Text, ScrollView, Pressable }} from "react-native";
import {{ Link }} from "expo-router";
import {{ theme }} from "../../lib/theme";

export default function HomeScreen() {{
  return (
    <ScrollView className="flex-1 bg-[#0f1117]" contentContainerStyle={{{{ padding: 20 }}}}>
      <View className="mb-6 rounded-2xl border border-white/10 p-6" style={{{{ backgroundColor: theme.card }}}}>
        <Text className="text-2xl font-bold text-white">{{app_name}}</Text>
        <Text className="mt-2 text-sm text-gray-400">Secteur : {sector}</Text>
        <View className="mt-4 h-1 rounded-full" style={{{{ backgroundColor: "{primary}", width: 64 }}}} />
      </View>
      <Text className="mb-3 text-xs font-semibold uppercase tracking-widest text-gray-500">
        Navigation rapide
      </Text>
      <Link href="/contact" asChild>
        <Pressable className="mb-3 rounded-xl border border-white/10 p-4" style={{{{ backgroundColor: theme.card }}}}>
          <Text className="font-semibold text-white">Nous contacter</Text>
          <Text className="mt-1 text-sm text-gray-400">Formulaire et coordonnées</Text>
        </Pressable>
      </Link>
    </ScrollView>
  );
}}
'''


def _generic_list_screen(title: str, items: list[str], primary: str) -> str:
    items_js = ",\n    ".join(f'{{ id: "{i}", label: "{label}" }}' for i, label in enumerate(items))
    return f'''import {{ useState }} from "react";
import {{ View, Text, FlatList, Pressable }} from "react-native";
import {{ theme }} from "../../lib/theme";

const ITEMS = [
    {items_js}
];

export default function Screen() {{
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <View className="flex-1 bg-[#0f1117] px-4 pt-6">
      <Text className="mb-4 text-xl font-bold text-white">{title}</Text>
      <FlatList
        data={{ITEMS}}
        keyExtractor={{(item) => item.id}}
        renderItem={{({{ item }}) => (
          <Pressable
            onPress={{() => setSelected(item.id)}}
            className="mb-3 rounded-xl border border-white/10 p-4"
            style={{{{ backgroundColor: selected === item.id ? "{primary}22" : theme.card }}}}
          >
            <Text className="font-medium text-white">{{item.label}}</Text>
          </Pressable>
        )}}
      />
    </View>
  );
}}
'''


def _auth_screen(primary: str) -> str:
    return f'''import {{ useState }} from "react";
import {{ View, Text, TextInput, Pressable, Alert }} from "react-native";
import {{ theme }} from "../../lib/theme";

export default function AuthScreen() {{
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");

  function handleSubmit() {{
    if (!email.trim() || !password.trim()) {{
      Alert.alert("Erreur", "Email et mot de passe requis.");
      return;
    }}
    Alert.alert("Succès", mode === "login" ? "Connexion réussie" : "Compte créé");
  }}

  return (
    <View className="flex-1 justify-center bg-[#0f1117] px-6">
      <Text className="mb-6 text-2xl font-bold text-white">
        {{mode === "login" ? "Connexion" : "Inscription"}}
      </Text>
      <TextInput
        className="mb-3 rounded-xl border border-white/10 px-4 py-3 text-white"
        style={{{{ backgroundColor: theme.card }}}}
        placeholder="Email"
        placeholderTextColor={theme.muted}
        value={{email}}
        onChangeText={{setEmail}}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      <TextInput
        className="mb-4 rounded-xl border border-white/10 px-4 py-3 text-white"
        style={{{{ backgroundColor: theme.card }}}}
        placeholder="Mot de passe"
        placeholderTextColor={theme.muted}
        value={{password}}
        onChangeText={{setPassword}}
        secureTextEntry
      />
      <Pressable
        onPress={{handleSubmit}}
        className="mb-3 rounded-xl py-3"
        style={{{{ backgroundColor: "{primary}" }}}}
      >
        <Text className="text-center font-semibold text-white">
          {{mode === "login" ? "Se connecter" : "Créer un compte"}}
        </Text>
      </Pressable>
      <Pressable onPress={{() => setMode(mode === "login" ? "register" : "login")}}>
        <Text className="text-center text-sm text-gray-400">
          {{mode === "login" ? "Créer un compte" : "Déjà inscrit ? Se connecter"}}
        </Text>
      </Pressable>
    </View>
  );
}}
'''


def _contact_screen(app_name: str, primary: str) -> str:
    return f'''import {{ useState }} from "react";
import {{ View, Text, TextInput, Pressable, Alert, ScrollView }} from "react-native";
import {{ theme }} from "../../lib/theme";

export default function ContactScreen() {{
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  function send() {{
    if (!name.trim() || !message.trim()) {{
      Alert.alert("Erreur", "Nom et message requis.");
      return;
    }}
    Alert.alert("Merci", "Votre message a été envoyé à {app_name}.");
    setName("");
    setMessage("");
  }}

  return (
    <ScrollView className="flex-1 bg-[#0f1117] px-4 pt-6">
      <Text className="mb-4 text-xl font-bold text-white">Contact</Text>
      <TextInput
        className="mb-3 rounded-xl border border-white/10 px-4 py-3 text-white"
        style={{{{ backgroundColor: theme.card }}}}
        placeholder="Votre nom"
        placeholderTextColor={theme.muted}
        value={{name}}
        onChangeText={{setName}}
      />
      <TextInput
        className="mb-4 rounded-xl border border-white/10 px-4 py-3 text-white"
        style={{{{ backgroundColor: theme.card }}}}
        placeholder="Votre message"
        placeholderTextColor={theme.muted}
        value={{message}}
        onChangeText={{setMessage}}
        multiline
        numberOfLines={5}
        textAlignVertical="top"
      />
      <Pressable onPress={{send}} className="rounded-xl py-3" style={{{{ backgroundColor: "{primary}" }}}}>
        <Text className="text-center font-semibold text-white">Envoyer</Text>
      </Pressable>
    </ScrollView>
  );
}}
'''


def _screen_content(screen: dict[str, str], app_config: dict[str, Any]) -> str:
    """Génère le contenu TSX d'un écran selon son identifiant."""
    route = screen["route"]
    title = screen["title"]
    app_name = str(app_config.get("name") or "App")
    primary = str(app_config.get("primary_color") or "#06b6d4")
    sector = str(app_config.get("sector") or "vitrine")

    if route in ("index", "home"):
        return _home_screen(app_name, sector, primary)
    if route == "auth":
        return _auth_screen(primary)
    if route == "contact":
        return _contact_screen(app_name, primary)

    sector_data: dict[str, list[str]] = {
        "menu": ["Entrées du jour", "Plats principaux", "Desserts", "Boissons"],
        "reservation": ["Aujourd'hui 19h", "Demain 12h30", "Samedi 20h"],
        "commande": ["Menu du jour", "Formule déjeuner", "À emporter"],
        "devis": ["Devis cuisine", "Devis salle de bain", "Devis électricité"],
        "planning": ["Lundi — Intervention A", "Mercredi — Chantier B"],
        "clients": ["Martin SA", "Dupont SARL", "Bernard EI"],
        "interventions": ["Réparation fuite", "Installation chaudière"],
        "catalogue": ["Produit A", "Produit B", "Produit C"],
        "panier": ["Article 1", "Article 2"],
        "fidelite": ["Bronze — 50 pts", "Argent — 200 pts", "Or — 500 pts"],
        "rdv": ["Créneau 9h", "Créneau 14h", "Créneau 17h"],
        "suivi": ["Dossier #1024", "Dossier #1025"],
        "messagerie": ["Support", "Commercial"],
        "presentation": ["Notre histoire", "Nos valeurs", "L'équipe"],
        "galerie": ["Photo 1", "Photo 2", "Photo 3"],
        "avis": ["★★★★★ Excellent", "★★★★☆ Très bien"],
        "notifications": ["Rappel RDV", "Promo du jour"],
        "carte": ["Position actuelle", "Itinéraire"],
        "camera": ["Prendre une photo", "Scanner un code"],
        "paiement": ["Carte bancaire", "Apple Pay", "Google Pay"],
        "calendrier": ["Lun 10", "Mar 11", "Mer 12"],
        "chat": ["Support", "Assistant"],
        "offline": ["Données en cache", "Synchroniser"],
    }
    items = sector_data.get(route, [f"{title} — élément 1", f"{title} — élément 2"])
    return _generic_list_screen(title, items, primary)


def _offline_store() -> str:
    return '''import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";

interface OfflineState {
  cache: Record<string, string>;
  setCache: (key: string, value: string) => Promise<void>;
  loadCache: () => Promise<void>;
}

export const useOfflineStore = create<OfflineState>((set, get) => ({
  cache: {},
  setCache: async (key, value) => {
    const next = { ...get().cache, [key]: value };
    set({ cache: next });
    await AsyncStorage.setItem("@offline_cache", JSON.stringify(next));
  },
  loadCache: async () => {
    const raw = await AsyncStorage.getItem("@offline_cache");
    if (raw) set({ cache: JSON.parse(raw) });
  },
}));
'''


def build_file_map(app_config: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, str]], list[str]]:
    """Construit la carte des fichiers à générer."""
    app_id = str(app_config.get("id") or "")
    name = str(app_config.get("name") or "App")
    primary = str(app_config.get("primary_color") or "#06b6d4")
    secondary = str(app_config.get("secondary_color") or "#8b5cf6")
    sector = str(app_config.get("sector") or "vitrine")
    features = _normalize_features(app_config.get("features"))
    screens = _resolve_screens(sector, features)

    files: dict[str, str] = {
        "package.json": _package_json(name, features),
        "tsconfig.json": _tsconfig(),
        "babel.config.js": _babel_config(),
        "tailwind.config.js": _tailwind_config(),
        "global.css": _global_css(),
        "lib/theme.ts": _theme_ts(primary, secondary),
        "app/_layout.tsx": _root_layout(),
        "app/(tabs)/_layout.tsx": _tabs_layout(screens, primary),
    }

    if "offline_mode" in features:
        files["lib/offline.ts"] = _offline_store()

    for screen in screens:
        route = screen["route"]
        if route in ("index", "home"):
            files["app/(tabs)/index.tsx"] = _screen_content(screen, app_config)
        else:
            files[f"app/(tabs)/{route}.tsx"] = _screen_content(screen, app_config)

    # Écran auth hors tabs si activé
    if "auth" in features:
        files["app/auth.tsx"] = _auth_screen(primary)

    return files, screens, features


async def generate_mobile_app(app_config: dict[str, Any]) -> MobileGenerationResult:
    """
    Génère la structure complète React Native Expo et l'écrit sur disque.
    """
    app_id = str(app_config.get("id") or "").strip()
    if not app_id:
        raise ValueError("app_config.id requis")

    files, screens, features = build_file_map(app_config)
    root = generate_app_structure(app_config, files)
    bundle_id = str(app_config.get("bundle_id") or f"com.capcore.{app_config.get('app_slug', 'app')}")
    configure_eas(app_id, bundle_id, app_config)

    return MobileGenerationResult(
        app_id=app_id,
        files={**files, "app.json": "generated", "eas.json": "generated"},
        screens=screens,
        features=features,
        build_root=str(root),
    )


async def analyze_brief(app_config: dict[str, Any]) -> dict[str, Any]:
    """Analyse le brief et retourne un résumé structuré (sans LLM — déterministe)."""
    features = _normalize_features(app_config.get("features"))
    sector = str(app_config.get("sector") or "vitrine")
    screens = _resolve_screens(sector, features)
    return {
        "sector": sector,
        "mode": app_config.get("mode"),
        "features": features,
        "screens_count": len(screens),
        "features_count": len(features),
        "screens": screens,
    }
