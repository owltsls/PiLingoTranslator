# 本地权重目录（随安装包分发，运行时零下载）

作者联系方式 · 微信号：TheSun_Also_Rises

## 翻译模型（必需）

| 项 | 值 |
| --- | --- |
| 文件名 | `Hy-MT2-1.8B-Q4_K_M.gguf` |
| 体积 | 1,133,080,448 B ≈ 1.06 GiB |
| 来源 | 腾讯开源翻译模型（沿用本项目 V0.3 已核验档位） |
| 许可证 | Apache-2.0（原文归档见 `licenses/`） |
| 安装态位置 | `{app}\resources\models\bundled\Hy-MT2-1.8B-Q4_K_M.gguf` |
| 调用方式 | `llama-cpp-python` 进程内 CPU 推理；不启动服务、不监听端口 |

开发态为避免重复存放 1 GiB 文件，`app/config.py` 的 `resolve_model_path()` 会依次查找：

1. 设置里显式指定的 `model_path`；
2. 环境变量 `PILINGO_MODEL_PATH`；
3. 本目录 `resources/models/bundled/`；
4. 开发态回退：工作区内既有 `Π-Lingo/resources/models/bundled/` 的同一份权重。

也可在「设置 → 本地 GGUF 权重」里手动指定。**任何情况下都不会联网下载模型。**

## OCR 模型（M3 落地）

| 项 | 值 |
| --- | --- |
| 位置 | `resources/models/ocr/`（det.onnx / rec.onnx / cls.onnx） |
| 模型 | PP-OCRv5/v6 mobile 三件套，约 22 MB |
| 运行时 | RapidOCR + ONNX Runtime，OCR 侧整体约 100–200 MB |
| 一期语种 | 中英；其它语种按需另附识别模型 |

未放置模型时 OCR 功能在界面中明确显示"引擎未就绪"，不会静默降级为在线 OCR。
