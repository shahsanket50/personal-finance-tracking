# MoneyInsights - Native APK Build Guide

## Prerequisites
- [Android Studio](https://developer.android.com/studio) (latest version)
- JDK 17+
- Android SDK (installed via Android Studio)

## Quick Build Steps

### 1. Build the React app
```bash
cd frontend
yarn build
npx cap sync android
```

### 2. Open in Android Studio
```bash
npx cap open android
```

### 3. Generate APK
In Android Studio:
- **Build > Build Bundle(s) / APK(s) > Build APK(s)**
- Debug APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

### For Release APK (signed)
```bash
cd android
./gradlew assembleRelease
```
*Note: Release builds require a signing keystore. See [Android signing docs](https://developer.android.com/studio/publish/app-signing)*

## Development Workflow

### Live Reload (for development)
```bash
npx cap run android --livereload --external
```

### After code changes
```bash
yarn build && npx cap sync android
```

## Configuration
- **App ID**: `com.moneyinsights.app`
- **App Name**: `MoneyInsights`
- **Config file**: `capacitor.config.json`

## Customization
- **App icon**: Replace `android/app/src/main/res/mipmap-*/ic_launcher.png`
- **Splash screen**: Configure in `capacitor.config.json` under `plugins.SplashScreen`
- **Status bar**: Configure in `capacitor.config.json` under `plugins.StatusBar`

## Installed Capacitor Plugins
- `@capacitor/core` — Core runtime
- `@capacitor/android` — Android platform
- `@capacitor/app` — App lifecycle events
- `@capacitor/keyboard` — Keyboard management
- `@capacitor/splash-screen` — Native splash screen
- `@capacitor/status-bar` — Status bar control

## Troubleshooting
- **Gradle errors**: Open Android Studio > File > Sync Project with Gradle Files
- **White screen**: Ensure `webDir: "build"` in capacitor.config.json, and `yarn build` was run
- **API calls fail**: The app connects to the deployed backend URL set in `REACT_APP_BACKEND_URL`
