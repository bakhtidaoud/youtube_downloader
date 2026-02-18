; Inno Setup Script for UltraTube
[Setup]
AppName=UltraTube
AppVersion=1.0
DefaultDirName={pf}\UltraTube
DefaultGroupName=UltraTube
OutputDir=setup
OutputBaseFilename=UltraTubeSetup
Compression=lzma
SolidCompression=yes
SetupIconFile=resources\icon.ico

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\UltraTube.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\UltraTube"; Filename: "{app}\UltraTube.exe"
Name: "{commondesktop}\UltraTube"; Filename: "{app}\UltraTube.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\UltraTube.exe"; Description: "{cm:LaunchProgram,UltraTube}"; Flags: nowait postinstall skipifsilent
