# Build APK Android en local (Windows) — CyberForge Mobile

Guide pour compiler un **APK installable** sur Samsung (sans Play Store), **sans EAS cloud**.

Projet : `mobile/` — package `pro.capcore.cyberforge` — Expo SDK 54 — Yarn 1.22

---

## Quelle approche choisir ?

| Critère | EAS local (`eas build --local`) | Gradle direct (`expo prebuild` + `gradlew`) |
|---------|--------------------------------|---------------------------------------------|
| Prérequis SDK/JDK | Identiques | Identiques |
| Résolution dépendances | **Yarn local** (pas de `npm ci` EAS) | **Yarn local** |
| Configuration signing | EAS gère la keystore (assistant) | À configurer manuellement pour `release` |
| Première APK rapide (test) | Moyen | **Plus simple** (`assembleDebug`, pas de keystore) |
| APK release signée | **Recommandé** | Possible mais plus de config |

### Verdict — PC Windows **sans** Android Studio installé

**Les deux approches exigent le Android SDK.** Impossible de compiler un APK natif sans lui.

**Chemin le plus simple de bout en bout :**

1. **Installer Android Studio** (même si vous n’ouvrez pas l’IDE ensuite) — c’est le moyen le plus fiable d’obtenir SDK + outils sur Windows.
2. **Installer JDK 17** (ou utiliser le JBR fourni avec Android Studio).
3. Pour un **premier test rapide** : `expo prebuild` + `gradlew assembleDebug` (APK debug, installable, sans keystore).
4. Pour un **APK release** prêt à distribuer : `eas build --platform android --profile local --local` (signing guidé).

---

## 1. Prérequis Windows

### 1.1 Java JDK 17 (pas 21)

Télécharger **Eclipse Temurin 17** : https://adoptium.net/temurin/releases/?version=17

Ou utiliser le JDK embarqué d’Android Studio :

```text
C:\Program Files\Android\Android Studio\jbr
```

### 1.2 Android SDK (via Android Studio)

1. Télécharger **Android Studio** : https://developer.android.com/studio
2. Installer avec les options par défaut.
3. Au premier lancement : **SDK Manager** → installer :
   - Android SDK Platform **API 35** (ou la version ciblée par Expo 54)
   - Android SDK Build-Tools **35.0.0** (ou plus récent)
   - Android SDK Platform-Tools
   - Android SDK Command-line Tools

Emplacement SDK par défaut :

```text
C:\Users\<VOTRE_USER>\AppData\Local\Android\Sdk
```

### 1.3 Variables d’environnement (PowerShell admin, puis redémarrer le terminal)

Remplacer `<VOTRE_USER>` par votre nom d’utilisateur Windows.

```powershell
[System.Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\Program Files\Eclipse Adoptium\jdk-17.0.14.7-hotspot", "User")
[System.Environment]::SetEnvironmentVariable("ANDROID_HOME", "C:\Users\<VOTRE_USER>\AppData\Local\Android\Sdk", "User")
```

Si vous utilisez le JBR d’Android Studio :

```powershell
[System.Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\Program Files\Android\Android Studio\jbr", "User")
```

Ajouter au **PATH** utilisateur :

```text
%ANDROID_HOME%\platform-tools
%ANDROID_HOME%\tools
%ANDROID_HOME%\tools\bin
%ANDROID_HOME%\build-tools\35.0.0
%JAVA_HOME%\bin
```

Vérifier dans un **nouveau** PowerShell :

```powershell
java -version
# doit afficher version 17.x

adb version
# doit répondre sans erreur

echo $env:JAVA_HOME
echo $env:ANDROID_HOME
```

### 1.4 Outils Node / Expo / EAS

```powershell
cd C:\Users\mathi\cyberforge\mobile

npm install -g eas-cli
yarn install
eas login
```

---

## 2. Profil EAS local (`eas.json`)

Le profil `local` est déjà configuré :

```json
"local": {
  "distribution": "internal",
  "android": {
    "buildType": "apk",
    "gradleCommand": ":app:assembleRelease"
  }
}
```

---

## 3. Approche A — EAS build local (APK release signée)

Utilise **votre** `yarn.lock` local — pas d’install cloud.

```powershell
cd C:\Users\mathi\cyberforge\mobile

yarn install

eas build --platform android --profile local --local
```

**Premier build :** EAS propose de créer une **keystore Android** → choisir **Generate new keystore** et conserver le mot de passe.

**APK générée :** chemin affiché en fin de build, typiquement :

```text
C:\Users\mathi\cyberforge\mobile\build-xxxxxxxx.apk
```

**Installer sur Samsung :**

```powershell
adb install build-xxxxxxxx.apk
```

Ou copier l’APK sur le téléphone et l’ouvrir (autoriser « sources inconnues »).

---

## 4. Approche B — Gradle direct (sans EAS cloud, sans `eas build`)

### 4.1 Première APK de test (debug — le plus rapide)

Pas de keystore requise. Idéal pour valider que le SDK est bien configuré.

```powershell
cd C:\Users\mathi\cyberforge\mobile

yarn install

npx expo prebuild --platform android --clean
```

Génère le dossier `android/`.

```powershell
cd android

.\gradlew.bat assembleDebug
```

**APK produite :**

```text
android\app\build\outputs\apk\debug\app-debug.apk
```

Installer :

```powershell
adb install app\build\outputs\apk\debug\app-debug.apk
```

### 4.2 APK release (Gradle direct)

`assembleRelease` exige une **keystore**. Sans configuration, le build échoue.

Option simple : rester sur **Approche A** (`eas build --local`) pour la release signée.

Si vous voulez Gradle release manuel, créer une keystore :

```powershell
keytool -genkeypair -v -storetype PKCS12 -keystore cyberforge-release.keystore -alias cyberforge -keyalg RSA -keysize 2048 -validity 10000
```

Puis configurer `android/gradle.properties` et `android/app/build.gradle` (voir doc React Native « Signed APK »).

```powershell
cd C:\Users\mathi\cyberforge\mobile\android

.\gradlew.bat assembleRelease
```

**APK release :**

```text
android\app\build\outputs\apk\release\app-release.apk
```

---

## 5. Après installation sur le téléphone

1. Ouvrir **CyberForge** → **Paramètres**.
2. URL backend : `http://<IP-LAN-PC>:8002` (pas `127.0.0.1`).
3. Démarrer le backend CyberForge sur le PC.
4. Autoriser le port **8002** dans le pare-feu Windows si besoin.

Trouver l’IP du PC :

```powershell
ipconfig
# ex. 192.168.1.42 → http://192.168.1.42:8002
```

---

## 6. Dépannage

| Erreur | Solution |
|--------|----------|
| `JAVA_HOME is not set` | Redémarrer le terminal après avoir défini les variables |
| `SDK location not found` | Créer `android\local.properties` : `sdk.dir=C:\\Users\\<user>\\AppData\\Local\\Android\\Sdk` |
| `java version 21` alors que Gradle échoue | Forcer JDK 17 dans `JAVA_HOME` |
| `gradlew` introuvable | Utiliser `.\gradlew.bat` (Windows), pas `./gradlew` |
| Build release sans signing | Utiliser `assembleDebug` ou `eas build --local` |
| `yarn` introuvable | `npm install -g yarn` puis `yarn install` dans `mobile/` |
| Prebuild échoue | `npx expo prebuild --clean` depuis `mobile/` |

---

## 7. Récapitulatif des commandes

### Setup (une fois)

```powershell
# Installer Android Studio + JDK 17 + variables JAVA_HOME / ANDROID_HOME
cd C:\Users\mathi\cyberforge\mobile
yarn install
npm install -g eas-cli
eas login
```

### APK test rapide (recommandé en premier)

```powershell
cd C:\Users\mathi\cyberforge\mobile
npx expo prebuild --platform android --clean
cd android
.\gradlew.bat assembleDebug
adb install app\build\outputs\apk\debug\app-debug.apk
```

### APK release signée (distribution interne)

```powershell
cd C:\Users\mathi\cyberforge\mobile
eas build --platform android --profile local --local
adb install build-xxxxxxxx.apk
```

---

## 8. Fichiers à ne pas committer (optionnel)

Après `expo prebuild`, le dossier `android/` peut être régénéré. Ajouter à `.gitignore` si besoin :

```gitignore
/android
```

Le projet Expo managed actuel n’inclut pas `android/` tant que `prebuild` n’a pas été exécuté.
