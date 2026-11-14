# 模型获取与放置说明

本仓库**不包含任何模型权重**。翻译能力依赖一个 GGUF 文件，需要你自行从模型官方页面下载后放入指定目录。

> 为什么不随仓库分发：翻译模型约 **1.13 GB**，远超 GitHub 单文件 100 MB 上限；同时模型权重有独立的版权与许可证，由使用者直接从上游获取最清晰。 Releases 里的安装包**已内置**该权重，双击安装即可使用，无需任何下载。

---

## 一、必需：翻译模型（Hy-MT2-1.8B-Q4_K_M）

| 项 | 值 |
| --- | --- |
| 模型名 | Hy-MT2-1.8B（腾讯混元开源翻译模型） |
| 文件名（必须一致） | `Hy-MT2-1.8B-Q4_K_M.gguf` |
| 体积 | 1,133,080,448 字节 ≈ 1.06 GiB |
| 量化 | GGUF / Q4_K_M |
| 许可证 | Apache-2.0（原文见 `licenses/LICENSE-Hy-MT2.txt`） |
| 官方仓库 | <https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF> |
| 国内镜像 | <https://hf-mirror.com/tencent/Hy-MT2-1.8B-GGUF> |

### 下载方式 A：浏览器

打开官方仓库页面 → `Files and versions` → 下载 `Hy-MT2-1.8B-Q4_K_M.gguf`。

### 下载方式 B：命令行（推荐，支持断点续传）

```bash
# Hugging Face 官方
curl -L -C - -o Hy-MT2-1.8B-Q4_K_M.gguf \
  https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF/resolve/main/Hy-MT2-1.8B-Q4_K_M.gguf
```

```bash
# 国内网络可用镜像（内容一致）
curl -L -C - -o Hy-MT2-1.8B-Q4_K_M.gguf \
  https://hf-mirror.com/tencent/Hy-MT2-1.8B-GGUF/resolve/main/Hy-MT2-1.8B-Q4_K_M.gguf
```

### 下载后校验

文件大小应为 **1,133,080,448 字节**。用 PowerShell 核对：

```powershell
(Get-Item .\Hy-MT2-1.8B-Q4_K_M.gguf).Length
```

输出 `1133080448` 即完整。若明显偏小，说明下载中断，请重新执行上面的 `curl -C -` 续传。

---

## 二、放到哪里

程序按固定优先级查找权重，**放到第 1 项的位置最省事**。

### 从源码运行

```text
PiLingoTranslator/
└── resources/
    └── models/
        └── bundled/
            ├── Hy-MT2-1.8B-Q4_K_M.gguf     ← 把模型放这里
            ├── LICENSE-Hy-MT2.txt           （仓库已提供）
            └── README.md                    （仓库已提供）
```

即最终路径为：

```text
<仓库根目录>/resources/models/bundled/Hy-MT2-1.8B-Q4_K_M.gguf
```

### 使用安装包

安装包已内置权重，位于：

```text
%LOCALAPPDATA%\Programs\PiLingoTranslator\resources\models\bundled\Hy-MT2-1.8B-Q4_K_M.gguf
```

一般**无需手动放置**。只有在你自行构建、或换成别的量化档位时才需要替换该文件。

### 完整的查找顺序

`app/config.py` 的 `resolve_model_path()` 依次尝试，命中即停：

1. `settings.json` 中的 `model_path`（设置页可填）
2. 环境变量 `PILINGO_MODEL_PATH`（直接指向 .gguf 文件）
3. `<程序根>/resources/models/bundled/`
4. `<程序根>/_internal/resources/models/bundled/`
5. 冻结运行时：`<exe 目录>/resources/models/bundled/`
6. 冻结运行时：`<exe 目录>/_internal/resources/models/bundled/`
7. `<工程目录>/resources/models/bundled/`
8. 环境变量 `PILINGO_MODEL_DIR`（指向目录）
9. 开发态回退：`../Π-Lingo/resources/models/bundled/`

同一目录下存在多个 `.gguf` 时：优先文件名精确等于 `Hy-MT2-1.8B-Q4_K_M.gguf` 的那个，否则取体积最大的。

**任何情况下程序都不会联网下载模型。** 找不到权重时界面会明确提示「引擎未就绪」，不会伪造译文。

### 自检是否被正确识别

```bash
python main.py --model-info
```

输出会列出配置文件位置、显式路径、程序根目录、定位结果与命中的原因，最后一行 `可用 : 是` 即成功。

---

## 三、可选：OCR 模型

图片识别默认使用 **RapidOCR 自带的 PP-OCRv5/v6 mobile ONNX 模型**，随 `rapidocr-onnxruntime` 包一起安装，**不需要额外下载**。

只有在你想替换为自定义识别模型时，才需要在设置里填写「OCR 模型目录」，目录内需包含三个文件：

```text
<自定义目录>/
├── det.onnx    检测模型
├── rec.onnx    识别模型
└── cls.onnx    方向分类模型
```

留空则使用 RapidOCR 内置模型。OCR 依赖（`onnxruntime`、`opencv-python`、`numpy`、`Pillow`）由 `requirements.txt` 一并安装。

---

## 四、其它可选模型

`Hy-MT2-1.8B-GGUF` 仓库还提供 2bit / 1.25bit 等更小量化档。程序会扫描目录内任意 `.gguf` 并取体积最大者，因此**换成更小的档位同样能启动**，只是译文质量会下降。替换时注意：

- 文件名不必与默认一致，放在 `resources/models/bundled/` 即可被自动识别；
- 首次加载会在日志中打印实际使用的文件名；
- 本项目只在 Q4_K_M 档做过完整验收，其它档位属实验性使用。

---

## 五、许可证提醒

Hy-MT2 权重以 **Apache-2.0** 分发，版权归腾讯所有。你分发安装包或仓库发行版时，需要同时保留：

- `licenses/LICENSE-Hy-MT2.txt`（许可证原文）
- `licenses/NOTICE.txt`（版权归属与「已量化为 Q4_K_M」的修改说明）

并且**不得**使用「腾讯」「混元」「Hunyuan」作为你自己的产品名或图标，只能在技术说明中做事实性引用。
