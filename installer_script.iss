#define MyAppName "Ubahin"
#define MyAppVersion "0.1.1"
#define MyAppPublisher "Catalism-1"
#define MyAppExeName "Ubahin.exe"

[Setup]
AppId={{854A6F94-9CF8-47A0-96E8-CA8C1012D90F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/Catalism-1/UbahIn
AppSupportURL=https://github.com/Catalism-1/UbahIn
AppUpdatesURL=https://github.com/Catalism-1/UbahIn
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=dist\installer
OutputBaseFilename=Ubahin_Setup
SetupIconFile=assets\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes

[Files]
Source: "dist\Ubahin\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan Ubahin sekarang"; Flags: nowait postinstall skipifsilent

[Code]
var
  DeleteUserData: Boolean;

function InitializeUninstall(): Boolean;
begin
  DeleteUserData := False;
  if not UninstallSilent then
  begin
    DeleteUserData := MsgBox(
      'Hapus data pengguna Ubahin juga?' + #13#10#13#10 +
      'Ini mencakup settings, history, logs, dan cache di LOCALAPPDATA.',
      mbConfirmation,
      MB_YESNO
    ) = IDYES;
  end;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and DeleteUserData then
  begin
    DelTree(ExpandConstant('{localappdata}\Ubahin'), True, True, True);
  end;
end;
