; Inno Setup script for Beacon — per-user install (no admin).
;
; Installs to %LOCALAPPDATA%\Programs\Beacon so the in-app auto-update can
; replace the exe without elevation. Compile with the version passed in:
;   ISCC /DMyAppVersion=0.1.3 packaging\beacon.iss
; Produces dist\beacon-setup.exe.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "Beacon"
#define MyAppExeName "beacon.exe"
#define MyAppPublisher "Beacon"
#define MyAppURL "https://github.com/Kaslun/luxafor-flag-controller"

[Setup]
AppId={{F89166D6-E442-4A3A-AEDE-FACE7BE085B0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={localappdata}\Programs\Beacon
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=beacon-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Beacon is windowed; the installer should close a running copy before upgrade.
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
Name: "startup"; Description: "Start Beacon automatically when I sign in"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; "Start with Windows" — same Run value the in-app toggle manages, so the two
; stay consistent. Removed on uninstall.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "Beacon"; ValueData: """{app}\{#MyAppExeName}"""; \
  Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Beacon now"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; best-effort: stop a running instance before removing files
Filename: "{cmd}"; Parameters: "/c taskkill /im {#MyAppExeName} /f"; \
  Flags: runhidden; RunOnceId: "StopBeacon"
