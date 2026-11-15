# API Specification / API仕様書 v1.0

## Overview
The translation service exposes a local HTTP API on 127.0.0.1.
すべての通信は同一端末内で完結し、外部へ送信されません。

## Endpoints
- `POST /api/scan` scans a folder and lists candidate files.
- `POST /api/translate` returns rename or document plans per mode.
- `GET /api/health` reports whether the model is loaded.