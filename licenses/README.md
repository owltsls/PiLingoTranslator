# 许可证归档目录

作者联系方式 · 微信号：TheSun_Also_Rises ｜ 亦可通过仓库 Issues 反馈

本目录归档 π-Lingo 离线翻译所分发第三方组件的**许可证原文**。原则：原文逐仓库复制，不以自写摘要替代。

---

## 一、归档状态（2026-11-14）

| 文件 | 许可证 | 大小 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| `LICENSE-Hy-MT2.txt` | Apache-2.0 | 11,639 B | 已归档 | 含 Tencent 版权头 + Apache-2.0 全文 |
| `LICENSE-PaddleOCR.txt` | Apache-2.0 | 11,376 B | 已归档 | 上游 PaddleOCR 根目录 LICENSE |
| `LICENSE-RapidOCR.txt` | Apache-2.0 | 11,422 B | 已归档 | 含 RapidOCR Authors 版权头 |
| `LICENSE-ONNXRuntime.txt` | MIT | 1,094 B | 已归档 | 来自 onnxruntime 发行包 |
| `LICENSE-llama-cpp.txt` | MIT | 1,077 B | 已归档 | 来自 llama-cpp-python 0.3.36 发行包 |
| `LICENSE-Qt.txt` | LGPL-3.0 | 8,802 B | 已归档 | LGPL-3.0 全文 + 动态链接合规声明 |
| `NOTICE.txt` | — | — | 已归档 | 版权归属、量化改动、商标与署名汇总 |

> 另有仓库根目录 `LICENSE`：本软件自有代码（`app/`、`main.py`、`build/`、`preview/`、`tests/`）的 Apache-2.0 许可证全文。
> 仓库根目录 `THIRD_PARTY_NOTICES.md` 为面向 GitHub 读者的第三方组件清单与义务说明。

---

## 二、版本对应关系

| 组件 | 实际使用版本 | 上游仓库 / 来源 | 在本软件中的角色 |
| --- | --- | --- | --- |
| Hy-MT2-1.8B-Q4_K_M | GGUF / Q4_K_M，1,133,080,448 B | 腾讯混元 | 唯一翻译引擎 |
| PaddleOCR / PP-OCR 系列轻量模型 | det / rec / cls ONNX | github.com/PaddlePaddle/PaddleOCR | OCR 识别模型来源（模型版权归百度） |
| RapidOCR (onnxruntime) | 1.2.3 | github.com/RapidAI/RapidOCR | OCR 落地引擎 |
| ONNX Runtime | 1.31.1 | github.com/microsoft/onnxruntime | OCR 推理运行时 |
| PySide6 / Qt | 6.12.0 | Qt Company | 原生桌面窗口（动态链接，LGPL-3.0） |
| llama-cpp-python / llama.cpp | 0.3.36 | github.com/abetlen/llama-cpp-python | 进程内 GGUF 推理 |

---

## 三、原文来源与说明

| 文件 | 获取方式 |
| --- | --- |
| `LICENSE-Hy-MT2.txt` | 随模型权重归档的 Tencent 许可文件 |
| `LICENSE-PaddleOCR.txt` | `github.com/PaddlePaddle/PaddleOCR` 仓库根目录 LICENSE |
| `LICENSE-RapidOCR.txt` | `github.com/RapidAI/RapidOCR` 仓库根目录 LICENSE |
| `LICENSE-ONNXRuntime.txt` | onnxruntime 发行包内 LICENSE |
| `LICENSE-llama-cpp.txt` | llama-cpp-python 0.3.36 发行包内 licenses/LICENSE.md |
| `LICENSE-Qt.txt` | `gnu.org/licenses/lgpl-3.0.txt`，末尾追加本软件动态链接声明 |

`LICENSE-Qt.txt` 末尾追加的是**使用声明**，未改动 LGPL-3.0 条款原文。

---

## 四、明确排除的组件

以下组件不打包、不分发，不在本目录归档范围：

- PaddleOCR-VL（2.1–3.8 GB 视觉语言模型）
- PaddlePaddle 训练／推理全框架（约 380 MB）
- PP-OCR 服务端模型组（约 177 MB）

---

## 五、发行前检查

```bash
# 应列出 6 个 LICENSE 文件与 1 个 NOTICE 文件，缺失项即为发行阻断项
ls -1 licenses/LICENSE-*.txt licenses/NOTICE.txt
```

同时确认仓库根目录存在 `LICENSE`、`NOTICE.txt`、`THIRD_PARTY_NOTICES.md`。
