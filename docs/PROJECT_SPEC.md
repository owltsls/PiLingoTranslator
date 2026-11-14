# π-Lingo 离线翻译 · 项目说明书（供确认稿）

> 版本：v1.7.3 ｜ 类型：Windows 桌面工具（PySide6 原生 Qt） ｜ 生成方式：从工程源码逐个模块核对后撰写
>
> **本文件是给你审阅的草稿**，所有数值均取自真实代码（`app/translator.py`、`app/ocr.py`、`app/config.py`、`app/text_logic.py`、`build/setup.iss`）。确认后我再据此生成正式版 README 与 GitHub 页面文案。

---

## 一、产品定位

一个**完全离线**的 Windows 翻译工具：模型权重随安装包分发，运行期零出站请求、零端口监听、零遥测。适合处理合同、内部文档、客户资料等不便上传到在线翻译服务的内容。

**不做的事**（同样是产品边界）：

- 不启动本地 HTTP 服务（不用 `llama-server`，不做 localhost 转发）；
- 不嵌入浏览器内核（不用 WebView / QWebEngineView）；
- 不监听剪贴板、不做划词取词（该模块 v1.7.x 已整体删除）；
- 不内置在线 OCR、不提供第三方 API 接入；
- 不在运行期下载任何模型或依赖。

---

## 二、核心功能

| 功能 | 行为说明 |
| --- | --- |
| 手动输入翻译 | 独立小窗输入/粘贴文本，**停止输入 1000 ms 自动翻译**；无翻译按钮、无快捷键 |
| 图片识别翻译 | 框选屏幕区域 → OCR 识别 → 自动翻译；原文/译文双栏对照 |
| 长文本分块 | 超过单块上限自动按段落 / 句末 / 空格切分，逐块回填，原文不截断 |
| 流式回填 | 后端的流式 token 逐个追加到译文区，界面不假死 |
| 可取消 | 翻译中可在块边界取消，已完成的译文保留 |
| 窗口置顶 | 两个翻译窗默认置顶，标题栏图钉可切换；Win32 `SetWindowPos` 实现，不抢焦点、不重建窗口 |
| 托盘常驻 | 关闭窗口不退出进程，托盘菜单提供两个入口 + 设置 + 关于 + 退出 |
| 中文界面 | 加载 Qt 官方 `qt_zh_CN.qm` / `qtbase_zh_CN.qm`，输入框右键菜单为中文 |
| 配置自愈 | `settings.json` 损坏/字段非法时自动恢复默认值并给出 warning，不崩溃 |
| 崩溃留痕 | `sys.excepthook` + `threading.excepthook` + Qt `notify` 兜底，异常写入 `crash.log` |
| 离线守卫 | 运行时 monkey-patch `socket.connect` 等，任何出站连接直接抛异常；启动自检静态扫描源码禁用网络调用 |

### 两个翻译窗的界面约定

- 左上角只有「手动输入翻译 / 图片识别翻译」纯文字标题 + 灰色小字注释，无装饰底色、无「设置」按钮；
- 底栏统一：左侧青色圆点状态提示 + 弹性留白 + 右下角「复制译文」（点击后 1.4 s 显示「已复制」）；
- 手动输入窗状态行右侧有「清空输入」；
- 标题栏 `□ / ■` 走 Windows 原生最大化 / 还原，四边可缩放；
- 每次打开手动输入窗强制回到小窗，不恢复上次最大化状态。

---

## 三、技术架构

```text
PySide6 / Qt Widgets（原生窗口，无 WebView）
        │
        ├─ 输入：键盘输入 · 屏幕框选截图（QScreen.grabWindow）
        │
        ├─ 能力层（进程内函数调用）
        │    ├─ Translator 单例 → LlamaCppBackend → llama-cpp-python → GGUF
        │    └─ OCRProvider    → RapidOCR → ONNX Runtime → det/rec/cls.onnx
        │
        └─ 逻辑层（纯 Python，可单测）
             config · text_logic · state_machine · offline_guard · hotkeys
```

**模型分工**：PP-OCR 只负责「认字」，Hy-MT2 只负责「翻译」，不引入第三个生成式模型。

---

## 四、参数配置（全部取自代码默认值）

### 4.1 翻译推理参数

| 参数 | 值 | 出处 |
| --- | --- | --- |
| 模型文件 | `Hy-MT2-1.8B-Q4_K_M.gguf`（1,133,080,448 B） | `branding.py` |
| 推理库 | `llama-cpp-python` ≥ 0.3.0，进程内加载 | `requirements.txt` |
| `n_ctx` | 2048 | `translator.py` |
| `n_gpu_layers` | 0（纯 CPU） | `translator.py` |
| `n_threads` | `min(8, os.cpu_count())`，下限 1 | `translator.py` |
| `temperature` | 0.0（确定性输出） | `translator.py` |
| `top_p` | 0.9 | `translator.py` |
| `repeat_penalty` | 1.05 | `translator.py` |
| `max_tokens` | `clamp(len(text) * 2 + 64, 128, 2048)` | `translator.py` |
| `use_mmap` | True（权重只读映射） | `translator.py` |
| 目标语言 | 简体中文（`zh-CN`） | `branding.py` |
| 分块上限 | 2000 字符/块 | `config.py` |

### 4.2 文本处理参数

| 参数 | 值 | 说明 |
| --- | --- | --- |
| 自动翻译延迟 | 1000 ms（常量，不可配置） | `AUTO_TRANSLATE_DELAY_MS` |
| 最小字符数 | 2 | `text_logic.should_skip()` |
| 长文本提示阈值 | > 500 字提示最大化；> 2000 字进入长文本模式 | `text_logic.long_text_hint()` |
| 分块边界优先级 | 换行 > 句末标点（`.!?。！？;；`）+ 空白 > 任何空白 > 硬切 | `split_blocks()` |
| 归一化 | `\r\n`→`\n`、去零宽字符、去行尾空白 | `normalize_selection()` |
| 路径过滤 | Windows 绝对路径 / UNC / URL / 含分隔符的全路径跳过（**单个文件名不过滤**） | `looks_like_path()` |

### 4.3 OCR 参数

| 参数 | 值 |
| --- | --- |
| 引擎 | RapidOCR（`rapidocr-onnxruntime`）+ ONNX Runtime |
| 模型 | PP-OCRv5/v6 mobile：`det.onnx` / `rec.onnx` / `cls.onnx` |
| 最小平均置信度 | 0.5（低于则提示重新框选，原文保留供核对） |
| 行聚类容差 | `y_tolerance = 12.0` px |
| 位图处理 | 只在内存中转 numpy 数组，不写临时文件 |

### 4.4 `settings.json` 全字段

路径：`%APPDATA%\PiLingoTranslator\settings.json`（可用环境变量 `PILINGO_CONFIG_DIR` 覆盖）

| 字段 | 默认值 | 范围 / 约束 |
| --- | --- | --- |
| `ocr_enabled` | `true` | bool |
| `hotkey_w3` | `Ctrl+Shift+I` | 合法热键，非法回默认 |
| `hotkey_ocr` | `Ctrl+Shift+O` | 合法热键，非法回默认 |
| `w3_visible` | `false` | bool |
| `w3_always_on_top` | `true` | bool |
| `w3_clear_on_close` | `false` | bool |
| `w3_maximized` | `false` | bool（运行期不写盘） |
| `ocr_window_always_on_top` | `true` | bool |
| `w3_geometry` | `{x:120, y:120, w:420, h:500}` | x/y ∈ [-10000, 20000]；w ∈ [320, 4000]；h ∈ [240, 3000] |
| `max_block_chars` | `2000` | [200, 10000] |
| `theme` | `light` | `light` / `dark` |
| `font_size` | `13` | [10, 24] |
| `model_path` | `""` | 留空走自动定位 |
| `ocr_model_dir` | `""` | 留空用 RapidOCR 自带模型 |
| `ocr_min_confidence` | `0.5` | [0.0, 1.0] |
| `source_language` | `auto` | `auto` 或 `xx` / `xx-XX` |
| `autostart` | `false` | bool |
| `history_enabled` | `false` | bool |
| `network_guard` | `true` | bool |
| `global_hotkeys` | `true` | bool |

> 配置读取使用「已知字段过滤 + 类型校验 + 范围夹紧」，未知字段（如已删除的 `listen_enabled`）会被静默忽略，不会导致启动失败。

### 4.5 模型路径解析优先级

`resolve_model_path()` 依次尝试：

1. `settings.model_path`（设置里显式指定）
2. 环境变量 `PILINGO_MODEL_PATH`
3. `<app_root>/resources/models/bundled/`
4. `<app_root>/_internal/resources/models/bundled/`
5. 冻结态：`<exe 目录>/resources/models/bundled/`、`<exe 目录>/_internal/...`
6. `<工程目录>/resources/models/bundled/`
7. 环境变量 `PILINGO_MODEL_DIR`
8. 开发态回退：`../Π-Lingo/resources/models/bundled/`

目录内若有多个 `.gguf`：优先文件名精确匹配 `Hy-MT2-1.8B-Q4_K_M.gguf`，否则取体积最大的一个。**任何情况下都不联网下载**。

### 4.6 命令行参数

| 参数 | 作用 |
| --- | --- |
| （无） | 正常启动，托盘常驻 |
| `--self-test` | 不启动 GUI 的逻辑自检，返回失败项数量 |
| `--offscreen` | 离屏构造全部窗口后立即退出（CI / 冒烟用） |
| `--translate TEXT` | 无头真实翻译一段文本 |
| `--model-info` | 打印权重搜索路径与命中结果 |
| `--version` | 版本与作者联系方式 |
| `--demo` | 演示模式，输出明确标记的占位文本（非真实译文） |
| `--no-hotkeys` / `--no-tray` | 不注册热键 / 不显示托盘 |
| `--config-dir PATH` | 指定配置目录 |

### 4.7 窗口最小尺寸（不可突破）

| 窗口 | 最小尺寸 |
| --- | --- |
| 手动输入翻译窗 | 420 × 520 |
| 图片识别翻译窗 | 480 × 420 |
| 设置 | 520 × 560 |
| 关于 | 560 × 460 |

---

## 五、仓库结构

```text
PiLingoTranslator/
├── main.py                 入口 / 自检 / CLI
├── app/
│   ├── branding.py         产品名、版本、引擎常量（唯一真源）
│   ├── config.py           Settings、校验、原子写、模型定位
│   ├── translator.py       Translator 单例 + LlamaCpp 后端 + 分块调度
│   ├── ocr.py              OCR Provider + 行整理 + OCRPipeline
│   ├── text_logic.py       归一化、路径过滤、语言检测、分块
│   ├── state_machine.py    极简 AppState / W3 状态机
│   ├── hotkeys.py          热键解析与注册
│   ├── offline_guard.py    运行时断网 + 源码静态扫描
│   ├── qt_i18n.py          Qt 中文翻译加载
│   ├── win_topmost.py      Win32 置顶
│   └── ui/                 theme / widgets / manual_window / ocr_window / dialogs / tray / app
├── tests/                  unittest（166 项）
├── build/                  spec / Inno Setup / 版本资源 / 构建脚本
├── preview/                布局体检与截图脚本（设计参考 HTML 仅存档）
├── resources/              图标、向导图、模型目录（权重不入库）
├── licenses/               第三方许可证原文
├── docs/                   项目说明、模型获取说明
├── LICENSE / NOTICE.txt / THIRD_PARTY_NOTICES.md
└── requirements.txt
```

---

## 六、开发与验收命令

```bash
pip install -r requirements.txt
python main.py --self-test                       # 逻辑自检
python main.py --offscreen                       # 离屏构造窗口
python main.py --translate "Hello, offline world"
python -m unittest discover -s tests -t .        # 全量单测
python preview/check_layout_sizes.py             # 4 窗体 × 3 档布局体检
python build/build_installer.py                  # 出安装包
```

当前基线：单测 166/166、自检 16/16、布局体检全通过。

---

## 七、已知限制（如实写在文档里）

1. **仅支持 Windows x64**（依赖 Win32 `SetWindowPos` 与 Inno Setup 安装包）；
2. **纯 CPU 推理**：1.8B Q4_K_M 在普通笔记本上约 2–6 秒/短句，长文本按块累加；
3. **目标语言固定为简体中文**，源语言由模型自动识别；
4. **OCR 一期只保证中英文**，其他语种需另配识别模型；
5. 译文由本地小模型生成，**不适用于医疗、法律、合同、证件等高风险场景**；
6. 安装包约 1.19 GB，首次安装受磁盘与杀软扫描影响可能较慢。

---

## 八、待你确认的三点

1. 上面「已知限制」是否要全部公开（建议保留，能显著降低售后沟通成本）；
2. 是否在 README 顶部加一张界面截图（`preview/shots/` 里有现成图，需要我做脱敏裁切）；
3. 作者联系方式保持「微信 + GitHub Issues」双通道，还是只留 Issues。
