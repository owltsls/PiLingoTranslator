# 第三方组件声明（THIRD PARTY NOTICES）

π-Lingo 离线翻译（PiLingoTranslator）在运行期／分发中包含以下第三方组件。
本文件为事实性署名与技术说明，各组件许可证原文归档于 `licenses/` 目录。

---

## 一、组件清单

| 组件 | 版本／文件 | 许可证 | 在本软件中的角色 | 上游来源 |
| --- | --- | --- | --- | --- |
| Hy-MT2-1.8B-GGUF | `Hy-MT2-1.8B-Q4_K_M.gguf` | Apache-2.0 | 唯一翻译引擎（进程内 CPU 推理） | 腾讯混元 · huggingface.co/tencent/Hy-MT2-1.8B-GGUF |
| PaddleOCR / PP-OCR mobile 识别模型 | det / rec / cls 三件套 ONNX | Apache-2.0（模型版权归百度） | OCR 识别模型来源 | github.com/PaddlePaddle/PaddleOCR |
| RapidOCR (onnxruntime) | 1.2.3 | Apache-2.0 | OCR 推理落地引擎 | github.com/RapidAI/RapidOCR |
| ONNX Runtime | 1.31.1 | MIT | OCR 推理运行时 | github.com/microsoft/onnxruntime |
| PySide6 / Qt for Python | 6.12.0 | LGPL-3.0（动态链接） | 原生桌面窗口与控件 | qt.io · github.com/qtproject/pyside-pyside-setup |
| llama-cpp-python / llama.cpp | 0.3.36 | MIT | 进程内加载 GGUF 权重 | github.com/abetlen/llama-cpp-python |

**构建期工具（不随运行期代码分发，不构成衍生作品）**：PyInstaller（GPL-2.0 + 打包例外条款）、Inno Setup（自有免费许可）。

---

## 二、必须履行的义务

### 1. Apache-2.0 组件（Hy-MT2、PaddleOCR 模型、RapidOCR）

- 随分发提供完整许可证原文，见 `licenses/LICENSE-Hy-MT2.txt`、`licenses/LICENSE-PaddleOCR.txt`、`licenses/LICENSE-RapidOCR.txt`；
- 保留原始版权、专利、商标与署名声明，不得移除；
- 对修改过的文件标注「已修改」；本软件对模型权重做过 **Q4_K_M 量化**（格式转换），已在本文与 `NOTICE` 中说明；
- 不得使用「腾讯 / 混元 / Hunyuan / 百度 / PaddleOCR」的名称或标识暗示官方背书、赞助或隶属关系，仅可作事实性描述（如「翻译引擎：Hy-MT2-1.8B」）。

### 2. MIT 组件（ONNX Runtime、llama-cpp-python）

- 随分发提供版权声明与许可原文，见 `licenses/LICENSE-ONNXRuntime.txt`、`licenses/LICENSE-llama-cpp.txt`。

### 3. LGPL-3.0 组件（PySide6 / Qt）

本软件以 **LGPL-3.0** 使用 Qt，并遵守以下条件：

1. **动态链接**：Qt 库以独立动态库（DLL）形式分发，未静态链接、未修改 Qt 本身；
2. **可替换性**：安装目录下 Qt 库文件可由用户自行替换（采用 PyInstaller onedir 分发，库文件位于 `_internal/PySide6/` 等目录，保持独立可见）；
3. **提供许可证原文**：`licenses/LICENSE-Qt.txt`（LGPL-3.0 全文）；
4. **提供源码获取途径**：Qt 源码见 download.qt.io/official_releases/qt/ 与 code.qt.io；PySide6 源码见 github.com/qtproject/pyside-pyside-setup；
5. **不限制逆向工程**：本软件许可条款不禁止为调试上述 LGPL 组件修改而进行的反向工程。

> LGPL 仅约束 Qt 组件本身，**不要求公开本软件自有源码**，也不禁止本软件收费分发。

---

## 三、离线与隐私

本软件 100% 本地运行：翻译与 OCR 均在本机完成，无端口监听、无 HTTP 路由、无出站请求、无遥测，不上传任何输入内容（手动输入文本、截图像素、OCR 中间结果）。运行期不下载任何模型或依赖，全部权重随安装包分发。

---

## 四、免责声明

1. 译文与 OCR 结果为本地模型自动生成，**仅供参考**，不构成专业意见。请勿直接用于医疗、法律、合同、证件、安全等高风险场景，由此产生的后果由使用者自行承担。
2. 本软件按「现状」（AS IS）提供，不附带任何明示或默示担保；作者不对翻译准确性、可用性及由此产生的任何直接或间接损失承担责任。
3. 本软件与腾讯、百度及其关联公司无隶属、赞助或背书关系。
