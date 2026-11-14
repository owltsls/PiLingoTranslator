# -*- coding: utf-8 -*-
"""品牌与作者信息的单一事实来源。

作者联系方式 · 微信号：TheSun_Also_Rises

所有界面、托盘、安装包元数据、版本信息与文档中的产品名和作者签名，
都必须引用本模块常量，禁止各文件自行硬编码，以免出现不一致。
"""
from __future__ import annotations

# ---------------------------------------------------------------- 产品
APP_NAME = "π-Lingo 离线翻译"
APP_NAME_ASCII = "PiLingo Offline Translator"
APP_ID = "pilingo-translator"
APP_VERSION = "1.7.3"
APP_STAGE = "M1/M2 可运行原型"
CONFIG_DIR_NAME = "PiLingoTranslator"

# ---------------------------------------------------------------- 作者签名
AUTHOR_SIGNATURE = "作者签名"
AUTHOR_LABEL = "作者联系方式"
AUTHOR_CONTACT_TYPE = "微信号"
AUTHOR_WECHAT = "TheSun_Also_Rises"
AUTHOR_CONTACT = f"{AUTHOR_LABEL} · {AUTHOR_CONTACT_TYPE}：{AUTHOR_WECHAT}"
AUTHOR_COPYRIGHT = f"Copyright © 2026 作者（{AUTHOR_CONTACT_TYPE}：{AUTHOR_WECHAT}）"

# ---------------------------------------------------------------- 引擎
TRANSLATION_ENGINE = "腾讯开源 Hy-MT2-1.8B-Q4_K_M"
TRANSLATION_MODEL_FILE = "Hy-MT2-1.8B-Q4_K_M.gguf"
TRANSLATION_MODEL_BYTES = 1_133_080_448
OCR_ENGINE = "RapidOCR + ONNX Runtime + PP-OCRv5/v6 mobile"
TARGET_LANGUAGE = "zh-CN"
TARGET_LANGUAGE_LABEL = "简体中文"
OFFLINE_SLOGAN = "100% 本地离线 · 零出站请求 · 无遥测"

# ---------------------------------------------------------------- 文案
def product_line() -> str:
    return f"{APP_NAME} v{APP_VERSION}（{APP_STAGE}）"


def signature_block() -> tuple[str, ...]:
    """关于页末尾的作者区块：放在正文最下面，只留联系方式本身。"""
    return (
        f"【{AUTHOR_LABEL}】",
        f"{AUTHOR_CONTACT_TYPE}：{AUTHOR_WECHAT}",
    )


def about_lines() -> tuple[str, ...]:
    """「关于」窗口正文：技术与许可说明。

    所有数值均取自本工程真实配置（translator.py / ocr.py / config.py /
    licenses/），不得编写无法在代码中核对的参数。用户定稿：正文**不含作者
    联系方式**（底栏已有可点击复制的签名），内容写全写专业、把窗口铺满。
    分区标题【】顶格，其下每个条目行缩进 2 个全角空格，形成清晰层次。
    """
    ind = "　　"  # 中文段落首行缩进 2 字符（约 24px）
    return (
        "【翻译模型】",
        ind + f"模型：{TRANSLATION_ENGINE}（18 亿参数，GGUF / Q4_K_M 量化）",
        ind + f"权重文件：{TRANSLATION_MODEL_FILE} · {TRANSLATION_MODEL_BYTES:,} B（随包分发）",
        ind + "许可：Apache-2.0（腾讯开源翻译模型）",
        "",
        "【推理配置】",
        ind + "运行时：llama-cpp-python / llama.cpp（MIT），进程内加载 GGUF，无服务、无端口",
        ind + "计算设备：CPU only（n_gpu_layers = 0），不依赖显卡驱动",
        ind + "上下文窗口：n_ctx = 2048；线程数按 CPU 核数自适应，上限 8",
        ind + "采样参数：temperature = 0.0，top_p = 0.9，repeat_penalty = 1.05",
        ind + "输出上限：max_tokens 按输入长度自适应，范围 128–2048",
        ind + "内存映射：use_mmap = True，权重只读映射，不复制、不联网下载",
        ind + "长文本：按 2000 字分块，逐块回填、块边界可取消，原文不截断",
        "",
        "【图片识别引擎】",
        ind + "引擎：RapidOCR（Apache-2.0）+ ONNX Runtime（MIT）",
        ind + "模型：PP-OCRv5/v6 mobile 轻量组（Apache-2.0，模型版权归百度飞桨团队）",
        ind + "结构：det / rec / cls 三个 ONNX 模型，进程内 CPU 推理",
        ind + "置信度：默认阈值 0.5，低于阈值的识别行会给出提示",
        "",
        "【离线与隐私】",
        ind + "100% 本地离线：翻译与 OCR 均在本机完成，零出站请求、无遥测",
        ind + "不上传选中文本 / 剪贴板 / 截图 / 手动输入内容；截图位图仅存内存、不落盘",
        ind + "运行时不下载任何模型或依赖，全部权重随安装包分发；网络守卫默认启用",
        "",
        "【界面与开源许可】",
        ind + "界面框架：PySide6 / Qt（LGPL / GPL 双授权，采用动态链接）",
        ind + "许可清单与离线声明：licenses/LICENSE_NOTICE.txt",
        ind + "完整许可证原文与 NOTICE 归档于 licenses/ 目录",
    )


def source_header() -> str:
    """源码文件头注释统一模板，保证作者签名随代码分发。"""
    return f"# {product_line()} ｜ {AUTHOR_CONTACT}"
