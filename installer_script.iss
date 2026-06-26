#define MyAppName "Ubahin"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Catalism-1"
#define MyAppExeName "Ubahin.exe"

[Setup]
AppId={{854A6F94-9CF8-47A0-96E8-CA8C1012D90F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=dist\installer
OutputBaseFilename=Ubahin_Setup
SetupIconFile=assets\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\Ubahin\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut tambahan:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Buka {#MyAppName}"; Flags: nowait postinstall skipifsilent
