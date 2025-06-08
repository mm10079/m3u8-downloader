# m3u8-downloader

一個基於 Python 的 M3U8 串流影片下載器，支援多線程、加密片段（AES-128）、合併 TS 檔案為 MP4，並能處理不同型態的 m3u8 網址格式。適用於需要批量下載 HLS 影片流的場景。

---

## 📦 功能特點

- ✅ 支援 AES-128 加密的 m3u8 串流
- ✅ 自動下載所有 `.ts` 檔案並合併為單一 MP4
- ✅ 支援相對與絕對 URL 的處理
- ✅ 支援多線程下載（加速處理）
- ✅ 使用 `ffmpeg` 合併音訊與影片
- ✅ 可處理直播或點播內容

---

## 🔧 安裝方式

1. 克隆此儲存庫：

```bash
git clone https://github.com/mm10079/m3u8-downloader.git
cd m3u8-downloader
```
2. 安裝所需套件：

```bash
pip install -r requirements.txt
```

3. 系統需安裝 ffmpeg 並加入環境變數或是放置於同exe資料夾路徑。

---
🚀 使用方式
基本命令如下：

```bash
python main.py -u <M3U8_URL> -o <OUTPUT_FILENAME>
```