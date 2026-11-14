; π-Lingo 离线翻译（独立软件）· Inno Setup 6.7.x 安装脚本
; 作者联系方式 · 微信号：TheSun_Also_Rises
; 完全离线：安装包内含本地权重，安装与运行均不需要联网。

#define MyAppName "π-Lingo 离线翻译"
#define MyAppShortName "PiLingoTranslator"
#define MyAppVersion "1.7.3"
#define MyAppPublisher "作者 · 微信号 TheSun_Also_Rises"
#define MyAppComments "作者联系方式 · 微信号：TheSun_Also_Rises ｜ 100% 本地离线 · 零出站请求"
#define MyAppExeName "PiLingoTranslator.exe"
#define MyCopyright "作者联系方式 · 微信号：TheSun_Also_Rises ｜ Hy-MT2 Apache-2.0 ｜ RapidOCR Apache-2.0"

[Setup]
AppId={{8F6A2D14-9C3E-4B7A-91D2-6C1E4A0B7F31}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments={#MyAppComments}
DefaultDirName={autopf}\{#MyAppShortName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=PiLingoTranslator_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
WizardStyle=modern
; 安装包本体 / 安装向导 / 卸载项全部使用设计定稿的新 icon
SetupIconFile=..\resources\PiLingo.ico
WizardImageFile=..\resources\wizard_large.png
WizardSmallImageFile=..\resources\wizard_small.png
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=完全本地离线的手动输入 / OCR 图片翻译工具
VersionInfoCopyright={#MyCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductTextVersion={#MyAppVersion}
LicenseFile=..\licenses\LICENSE_NOTICE.txt
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动（默认关闭的开关，可在设置里关闭）"; Flags: unchecked

[Files]
; 程序本体（PyInstaller 产物）
Source: "staging\*"; DestDir: "{app}"; Excludes: "*.gguf"; Flags: ignoreversion recursesubdirs createallsubdirs
; 本地权重：随包分发，运行时不下载
Source: "staging\resources\models\bundled\Hy-MT2-1.8B-Q4_K_M.gguf"; DestDir: "{app}\resources\models\bundled"; Flags: ignoreversion nocompression
; OCR 轻量模型（M3 落地后放开下行注释；约 22 MB）
; Source: "staging\resources\models\ocr\*"; DestDir: "{app}\resources\models\ocr"; Flags: ignoreversion
Source: "..\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion
; 快捷方式显式指定新 icon（不依赖 exe 内嵌图标的继承行为）
Source: "..\resources\PiLingo.ico"; DestDir: "{app}\resources"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\PiLingo.ico"
Name: "{group}\关于作者与联系方式"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--version"; IconFilename: "{app}\resources\PiLingo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\resources\PiLingo.ico"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart; IconFilename: "{app}\resources\PiLingo.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Messages]
WelcomeLabel2=正在安装 [name/ver]%n%n本软件完全本地离线运行：翻译与 OCR 均在本机完成，不上传任何文本或截图。%n%n作者联系方式 · 微信号：TheSun_Also_Rises

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    Log('π-Lingo 离线翻译：本地权重已安装，无需联网。作者联系方式 · 微信号：TheSun_Also_Rises');
end;
