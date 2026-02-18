# UltraTube Packaging Instructions

## 🪟 Windows (Inno Setup)
1. **Build EXE**: 
   ```powershell
   .\venv\Scripts\pyinstaller ultratube.spec
   ```
2. **Create Installer**: Open `installer.iss` in [Inno Setup](https://jrsoftware.org/isinfo.php) and click **Compile**.
3. **Output**: `setup/UltraTubeSetup.exe`

## 🍎 macOS (DMG)
1. **Install create-dmg**: `brew install create-dmg`
2. **Build App Bundle**:
   ```bash
   pyinstaller --windowed --name "UltraTube" --add-data "src:src" --icon "resources/icon.icns" main.py
   ```
3. **Create DMG**:
   ```bash
   create-dmg \
     --volname "UltraTube Installer" \
     --window-pos 200 120 \
     --window-size 800 400 \
     --icon-size 100 \
     --icon "UltraTube.app" 200 190 \
     --hide-extension "UltraTube.app" \
     --app-drop-link 600 185 \
     "dist/UltraTube.dmg" \
     "dist/"
   ```

## 🐧 Linux (AppImage)
1. **Build Binary**:
   ```bash
   pyinstaller --onefile --windowed --name "UltraTube" --add-data "src:src" main.py
   ```
2. **Create AppImage**: Use [linuxdeploy](https://github.com/linuxdeploy/linuxdeploy) with the Qt plugin:
   ```bash
   ./linuxdeploy-x86_64.AppImage --appdir AppDir -e dist/UltraTube -i resources/icon.png -d resources/ultratube.desktop --output appimage
   ```

## 📦 Requirements
- **FFmpeg**: Users must have FFmpeg installed or you should bundle `ffmpeg.exe` in the `added_files` section of `ultratube.spec`.
- **Resources**: Ensure the `resources/` folder exists with `icon.ico`, `icon.icns`, and `icon.png`.
