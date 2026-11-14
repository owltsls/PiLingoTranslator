# π-Lingo 离线翻译（PiLingoTranslator）

> **100% 本地离线** 的 Windows 桌面翻译工具 · **v1.7.3**
>
> 作者：TheSun_Also_Rises ｜ 微信：`TheSun_Also_Rises` ｜ 反馈：GitHub Issues

π-Lingo 是一款完全离线运行的 Windows 桌面翻译软件。翻译与图片文字识别全部在本机完成：**不联网、不监听端口、不上传任何输入内容**。

软件提供两个入口：

- **手动输入翻译**：在独立小窗中输入或粘贴文本，停止输入 1 秒后自动翻译；
- **图片识别翻译**：框选屏幕区域，识别图中文字并翻译，原文与译文双栏对照。

翻译引擎为腾讯开源的 **Hy-MT2-1.8B**（GGUF / Q4_K_M 量化，约 1.13 GB），通过 `llama-cpp-python` 在进程内以 CPU 推理；OCR 使用 **RapidOCR + ONNX Runtime** 与 PP-OCR 系列轻量模型。界面为 **PySide6 / Qt Widgets** 原生桌面程序，不使用 WebView、不启动本地 HTTP 服务。

---

## 目录

- [核心特性](#核心特性)
- [隐私与离线声明](#隐私与离线声明)
- [下载与安装](#下载与安装)
- [快速开始](#快速开始)
- [使用方式](#使用方式)
- [技术架构](#技术架构)
- [目录结构](#目录结构)
- [构建安装包](#构建安装包)
- [许可证](#许可证)
- [免责声明](#免责声明)
- [致谢](#致谢)

---

## 核心特性

| 特性 | 说明 |
| --- | --- |
| 完全离线 | 翻译与 OCR 均在本机完成，无出站请求、无遥测、无账号 |
| 零端口监听 | 不启动 HTTP 服务、不注册本地路由，输入内容不出本机 |
| 输入即译 | 手动输入窗停止输入 1 秒自动翻译，无需点击按钮 |
| 图片翻译 | 屏幕框选截图，识别中英文并翻译，原文/译文对照 |
| 原生界面 | PySide6 / Qt Widgets，无浏览器内核、无 WebView |
| 本地模型 | Hy-MT2-1.8B-Q4_K_M 随安装包分发，安装后无需联网下载 |
| 中文界面 | 内置 Qt 官方中文翻译，右键菜单与标准控件均为中文 |
| 安装即用 | Inno Setup 安装包，支持当前用户静默安装 |

---

## 隐私与离线声明

这是本软件最重要的设计约束：

1. **零出站请求**：运行时不访问任何网络地址，翻译与 OCR 均通过进程内函数调用完成；
2. **零端口监听**：不启动 `llama-server`、不监听 localhost、不注册 HTTP 路由；
3. **不上传内容**：手动输入文本、截图像素、OCR 中间结果均只存在于本机内存/本地配置；
4. **不监听剪贴板**：本版本不包含划词或剪贴板取词功能；
5. **无遥测**：不收集使用统计、设备信息或崩溃日志；
6. **权重随包**：安装包内已包含翻译模型与 OCR 模型，运行期不下载任何文件。

> 如发现任何联网行为，请通过 Issues 反馈，这属于必须修复的缺陷。

---

## 下载与安装

### 使用安装包（推荐）

前往仓库 **Releases** 下载：

```text
PiLingoTranslator_Setup_v1.7.3.exe
```

安装包约 1.19 GB（含翻译模型与 OCR 模型）。双击安装，或使用当前用户静默安装：

```powershell
.\PiLingoTranslator_Setup_v1.7.3.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER
```

默认安装目录：`%LOCALAPPDATA%\Programs\PiLingoTranslator`。

### 从源码运行

```bash
python -m pip install -r requirements.txt
python main.py --self-test
python main.py
```

> 开发态依赖可放在工作区 `.vendor*` 目录，`main.py` 会自动加入 `sys.path`。
> 源码仓库不包含 `.gguf` 模型权重，请从 Releases 或模型官方页面获取后放入 `resources/models/bundled/`。

---

## 快速开始

```bash
# 逻辑自检（不需要 GUI / 模型）
python main.py --self-test

# 离屏构造全部窗口（不弹窗，验证 UI 可启动）
python main.py --offscreen

# 正常启动（托盘常驻）
python main.py

# 无头真实翻译（不启动界面）
python main.py --translate "Hello, offline world"

# 查看版本与模型信息
python main.py --version
python main.py --model-info

# 全量单元测试
python -m unittest discover -s tests -t .
```

---

## 使用方式

### 托盘菜单

- **手动输入翻译**：打开手动输入翻译窗；
- **图片识别翻译**：进入屏幕框选，识别并翻译；
- **设置**：快捷键与窗口偏好；
- **关于**：版本、引擎与许可证说明；
- **退出**：结束程序。

### 默认全局快捷键

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl+Shift+I` | 打开手动输入翻译窗 |
| `Ctrl+Shift+O` | 截图 OCR 翻译 |

> 如与系统或其他软件冲突，可在「设置」中修改。

### 手动输入翻译窗

- 输入或粘贴文本，停止输入 1 秒后自动翻译；
- 右上角 `□ / ■` 为 Windows 原生最大化 / 还原；
- 标题栏可拖动，四边可缩放；
- 底栏右侧「复制译文」，左侧状态提示同步显示翻译状态；
- 状态行右侧「清空输入」可一键清空。

### 图片识别翻译窗

- 框选屏幕区域后自动识别并翻译；
- 原文与译文双栏对照；
- 标题栏「置顶常驻」图钉可切换窗口置顶；
- 「选择新的截图区域」可重新框选；
- 底栏右侧「复制译文」。

---

## 技术架构

```text
┌─ 原生桌面 UI（PySide6 / Qt Widgets）──────────────────────────┐
│ 手动输入翻译窗 · 图片识别翻译窗 · 设置 · 关于 · 系统托盘        │
├─ 输入层 ──────────────────────────────────────────────────────┤
│ 键盘输入 · 屏幕框选截图                                       │
├─ 能力层（进程内函数调用，无 HTTP / 无端口）───────────────────┤
│ Translator 单例 → Hy-MT2-1.8B-Q4_K_M（llama-cpp-python）      │
│ OCRProvider   → RapidOCR + ONNX Runtime + PP-OCR 轻量模型      │
├─ 逻辑层（纯 Python，可单测）───────────────────────────────────┤
│ config · text_logic · state_machine · offline_guard · hotkeys  │
├─ 本地权重（随安装包分发）─────────────────────────────────────┤
│ Hy-MT2 ≈1.13 GB ｜ OCR 模型 ≈13 MB                            │
└───────────────────────────────────────────────────────────────┘
```

**模型分工**：PP-OCR 系列轻量模型只负责「认字」，Hy-MT2 只负责「翻译」，不引入第三个生成式模型。

---

## 目录结构

```text
PiLingoTranslator/
├── main.py                      入口 + 自检 + CLI
├── app/
│   ├── branding.py              产品名 / 版本 / 作者签名
│   ├── config.py                配置模型、损坏恢复、原子写、模型路径解析
│   ├── hotkeys.py               全局热键解析与 Windows 注册
│   ├── offline_guard.py         运行时网络阻断 + 源码静态扫描
│   ├── text_logic.py            过滤、语言检测、无损分块、去抖
│   ├── state_machine.py         翻译状态机
│   ├── translator.py            Translator 单例、可插拔后端、分块调度
│   ├── ocr.py                   OCRProvider、RapidOCR、行整理
│   ├── qt_i18n.py               Qt 官方中文翻译加载
│   ├── win_topmost.py           Win32 置顶（不抢焦点）
│   └── ui/                      theme / widgets / manual_window /
│                               ocr_window / dialogs / tray / app
├── tests/                       unittest 逻辑与 UI 冒烟测试
├── build/                       PyInstaller spec、Inno Setup、版本资源、构建脚本
├── resources/models/            本地权重目录（权重不入库）
├── licenses/                    许可证原文与 NOTICE
├── LICENSE                      自有代码 Apache-2.0
├── NOTICE.txt                   第三方组件归属与修改说明
└── THIRD_PARTY_NOTICES.md       第三方组件清单与义务
```

---

## 构建安装包

### 环境

- Windows 10 / 11 x64
- Python 3.13
- PySide6 6.12、PyInstaller 6、Inno Setup 6
- 翻译模型 `Hy-MT2-1.8B-Q4_K_M.gguf` 放入 `resources/models/bundled/`

### 命令

```bash
python -m unittest discover -s tests -t .
python main.py --self-test
python preview/check_layout_sizes.py
python build/build_installer.py
```

产物：

```text
dist_installer/PiLingoTranslator_Setup_v1.7.3.exe
```

构建脚本会校验关键文件、模型权重与资源完整性，任何缺失都会中止打包。

---

## 许可证

### 本软件自有代码

`app/`、`main.py`、`build/`、`preview/`、`tests/` 等自有代码以 **Apache License 2.0** 授权，全文见仓库根目录 `LICENSE`。

Apache-2.0 允许：商业使用、修改、再分发、收费分发。你需要在分发时保留版权声明、许可证原文与 NOTICE，并不得使用原作者名义为你的产品背书。

### 第三方组件

| 组件 | 许可证 | 说明 |
| --- | --- | --- |
| Hy-MT2-1.8B-GGUF | Apache-2.0 | 腾讯开源翻译模型 |
| PaddleOCR / PP-OCR 模型 | Apache-2.0 | 模型版权归百度 |
| RapidOCR | Apache-2.0 | OCR 推理引擎 |
| ONNX Runtime | MIT | OCR 推理运行时 |
| PySide6 / Qt | LGPL-3.0 | 动态链接使用 |
| llama-cpp-python / llama.cpp | MIT | 进程内 GGUF 推理 |

许可证原文归档于 `licenses/`，完整义务说明见 `THIRD_PARTY_NOTICES.md`。

### Qt / LGPL-3.0 合规说明

1. 本软件以**动态链接**方式使用 Qt，未修改 Qt 本身，未做静态链接；
2. Qt 库以独立 DLL 形式位于安装目录 `_internal/` 下，用户可自行替换；
3. `licenses/LICENSE-Qt.txt` 提供 LGPL-3.0 全文与 Qt 源码获取途径；
4. LGPL 仅约束 Qt 组件，不要求公开本软件自有源码，也不禁止本软件收费分发。

### 模型权重

`Hy-MT2-1.8B-Q4_K_M.gguf` 以 Apache-2.0 分发，版权归腾讯所有。模型权重体积超过 GitHub 单文件上限，仓库不直接存放，请通过 Releases 资产获取；分发时需同时保留 `licenses/LICENSE-Hy-MT2.txt` 与 `NOTICE.txt`。

---

## 免责声明

1. 译文与 OCR 结果由本地模型自动生成，**仅供参考**，不构成专业意见。请勿直接用于医疗、法律、合同、证件、安全等高风险场景；由此产生的后果由使用者自行承担。
2. 本软件按「现状」（AS IS）提供，不附带任何明示或默示担保；作者不对翻译准确性、可用性及由此产生的任何直接或间接损失承担责任。
3. 本软件与腾讯、百度及其关联公司无隶属、赞助或背书关系。相关名称与商标归其各自权利人所有。

---

## 致谢

- 腾讯混元团队开源 Hy-MT2 翻译模型；
- 百度飞桨团队开源 PaddleOCR 与 PP-OCR 模型；
- RapidOCR、ONNX Runtime、llama.cpp / llama-cpp-python、PySide6 / Qt 等开源项目。

---

## 联系作者

- 微信：`TheSun_Also_Rises`
- 反馈：GitHub Issues
