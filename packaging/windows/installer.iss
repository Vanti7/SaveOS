; Script Inno Setup pour l'installeur Windows de l'agent SaveOS.
; Compile un installeur graphique par-dessus dist/saveos-agent.exe
; (construit au préalable via packaging/saveos-agent.spec).
;
; Invocation (depuis la racine du dépôt, ISCC dans le PATH) :
;   iscc packaging/windows/installer.iss /DMyAppVersion=1.5.0

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "SaveOS Agent"
#define MyAppPublisher "SaveOS Project"
#define MyAppExeName "saveos-agent.exe"

[Setup]
AppId={{7C1B6C9E-3B2A-4E7B-9C1D-5A2F8E4B6D10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SaveOS Agent
DefaultGroupName=SaveOS Agent
DisableProgramGroupPage=yes
; Élévation requise : écriture dans Program Files et enregistrement
; d'une tâche planifiée exécutée sous le compte SYSTEM.
PrivilegesRequired=admin
OutputDir=..\..\dist\installers
OutputBaseFilename=SaveOS-Agent-Setup-{#MyAppVersion}-windows
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\dist\saveos-agent.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Enregistre l'agent comme tâche planifiée à démarrage automatique.
Filename: "{app}\{#MyAppExeName}"; Parameters: "service install"; \
    StatusMsg: "Enregistrement du service SaveOS Agent..."; Flags: runhidden

[UninstallRun]
; Retire proprement la tâche planifiée avant de supprimer les fichiers.
Filename: "{app}\{#MyAppExeName}"; Parameters: "service stop"; Flags: runhidden; RunOnceId: "StopService"
