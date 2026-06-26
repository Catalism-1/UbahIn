#define MyAppName "Ubahin"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Ubahin"
#define MyAppExeName "Ubahin.exe"

[Setup]
AppId={{854A6F94-9CF8-47A0-96E8-CA8C1012D90F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist\installer
OutputBaseFilename=Ubahin_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\Ubahin\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut tambahan:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Buka {#MyAppName}"; Flags: nowait postinstall skipifsilent
