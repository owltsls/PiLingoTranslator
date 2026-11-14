# 翻译模型放置目录

**本目录不包含 `.gguf` 权重文件。** 请自行下载后放到这里。

## 需要下载的文件

| 项 | 值 |
| --- | --- |
| 文件名 | `Hy-MT2-1.8B-Q4_K_M.gguf` |
| 大小 | 1,133,080,448 字节（约 1.06 GiB） |
| 来源 | 腾讯混元 Hy-MT2-1.8B（Apache-2.0） |
| 官方仓库 | https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF |
| 国内镜像 | https://hf-mirror.com/tencent/Hy-MT2-1.8B-GGUF |

## 放置后的目录结构

```text
resources/models/bundled/
├── Hy-MT2-1.8B-Q4_K_M.gguf    ← 下载后放在这里（必需）
├── LICENSE-Hy-MT2.txt         仓库已提供
├── NOTICE.txt                 仓库已提供
└── README.md                  本文件
```

## 下载命令

```bash
# Hugging Face 官方（支持断点续传）
curl -L -C - -o Hy-MT2-1.8B-Q4_K_M.gguf \
  https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF/resolve/main/Hy-MT2-1.8B-Q4_K_M.gguf
```

```bash
# 国内网络可用镜像
curl -L -C - -o Hy-MT2-1.8B-Q4_K_M.gguf \
  https://hf-mirror.com/tencent/Hy-MT2-1.8B-GGUF/resolve/main/Hy-MT2-1.8B-Q4_K_M.gguf
```

## 校验

```powershell
(Get-Item .\Hy-MT2-1.8B-Q4_K_M.gguf).Length   # 应为 1133080448
```

## 确认程序能否找到模型

```bash
python main.py --model-info
```

完整说明见仓库根目录 `docs/MODELS.md`。

> **许可证**：模型权重以 Apache-2.0 分发，版权归腾讯所有。再分发时请保留本目录下的 `LICENSE-Hy-MT2.txt` 与 `NOTICE.txt`，并注明已量化为 Q4_K_M。
