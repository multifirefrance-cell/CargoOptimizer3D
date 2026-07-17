; Instalador de CargoOptimizer3D Beta (Inno Setup 6) — ver ADR-0013.
;
; Empaqueta la distribución "onedir" ya construida por PyInstaller
; (dist\CargoOptimizer3D\, generada por scripts\build_windows_beta.bat),
; no compila nada de Python: este script solo debe ejecutarse DESPUES
; de un build de PyInstaller exitoso.
;
; Compilar:
;   "C:\...\Inno Setup 6\ISCC.exe" packaging\installer.iss
; desde la raíz del repo (usa rutas relativas a #SourcePath).

#define MyAppName "CargoOptimizer3D"
#define MyAppVersion "1.0.0b2"
#define MyAppPublisher "CargoOptimizer3D"
#define MyAppExeName "CargoOptimizer3D.exe"
#define MyDistDir "..\dist\CargoOptimizer3D"
#define MyIconFile "app_icon.ico"

[Setup]
; GUID fijo: identifica esta aplicación entre versiones para que
; Inno Setup reconozca una actualización (no una instalación nueva) y
; nunca borre {app} en una actualización sin más.
AppId={{6C7B9C1B-6E9E-4E2E-8A9B-6C6A0B6C7A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\dist\installer
OutputBaseFilename=CargoOptimizer3D_Beta_Setup
SetupIconFile={#MyIconFile}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; La instalación en Program Files exige privilegios de administrador.
PrivilegesRequired=admin
VersionInfoVersion=1.0.0.0
VersionInfoProductName={#MyAppName}
VersionInfoProductTextVersion={#MyAppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Todo el contenido de la distribución onedir, preservando subcarpetas
; (resources, bibliotecas nativas de VTK/PySide6, etc.).
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; No hay sección [UninstallDelete]: los datos del usuario
; (%LOCALAPPDATA%\CargoOptimizer3D — SQLite, QSettings, proyectos que
; el usuario haya guardado ahí) viven fuera de {app} y Inno Setup no
; los toca por defecto. La eliminación es opcional y solo ocurre si el
; usuario confirma explícitamente en el diálogo posterior a
; desinstalar (ver [Code] más abajo) — nunca por defecto.

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataDir: String;
  Response: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    UserDataDir := ExpandConstant('{localappdata}\CargoOptimizer3D');
    if DirExists(UserDataDir) then
    begin
      Response := MsgBox(
        'Se conservaron tus proyectos, catálogo y configuración en:' + #13#10 +
        UserDataDir + #13#10 + #13#10 +
        '¿Deseas eliminar también estos datos? Esta acción no se puede deshacer.',
        mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
      if Response = IDYES then
        DelTree(UserDataDir, True, True, True);
    end;
  end;
end;
