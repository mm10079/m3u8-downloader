# m3u8-downloader

一個基於 Python 的 M3U8 串流影片下載器，支援多線程、加密片段（AES-128）、合併 TS 檔案為 MP4，並能處理不同型態的 m3u8 網址格式。適用於需要批量下載 HLS 影片流的場景。

---

## 📦 功能特點

- ✅ 支援Selenium模擬瀏覽器，自動捕獲 m3u8 網址
- ✅ 支援 AES-128 加密的 m3u8 串流
- ✅ 自動下載所有 `.ts` 檔案並合併為單一 MP4
- ✅ 支援相對與絕對 URL 的處理
- ✅ 支援多線程下載（加速處理）
- ✅ 使用 `ffmpeg` 合併音訊與影片
- ✅ 可處理直播或點播內容

---

## 🔧 安裝方式 Python

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
python main.py -u <M3U8_URL | WEB_URL> -o <OUTPUT_FILENAME>
```

## 🔧 使用方式

```
1. 直接執行 m3u8下載器.exe
2. 使用batch或CLI輸入參數啟動：m3u8下載器.exe --env ...
```

## 環境參數：
<table>
  <tr>
    <th>參數</th><th>名稱</th><th>功能</th>
  </tr>
  <tr>
    <td>URL</td><td>m3u8網址/網站網址</td><td>輸入m3u8網址會直接進入下載，輸入網站網址則會啟動瀏覽器，留空默認啟用瀏覽器</td>
  </tr>
  <tr>
    <td>--title "str"</td><td>檔案名稱</td><td>若無法從瀏覽器取得名稱，則選用此值為檔案名稱</td>
  </tr>
  <tr>
    <td>--quantity int</td><td>畫質排序數值</td><td>0為最高畫質，遞增而畫質降低</td>
  </tr>
  <tr>
    <td>--output-path "str"</td><td>存檔路徑</td><td>預設為downloads</td>
  </tr>
  <tr>
    <td>--cookies_path "str"</td><td>cookies路徑</td><td>直接下載m3u8時使用，若從瀏覽器捕捉m3u8，則自動從瀏覽器取得</td>
  </tr>
  <tr>
    <td>--tool-path "str"</td><td>FFmpeg路徑</td><td>預設為ffmpeg，exe檔已包裝ffmpeg無須設定</td>
  </tr>
  <tr>
    <td>--decrypt bool</td><td>解密碎片</td><td>在下載中途同時解密當前已有的碎片</td>
  </tr>
  <tr>
    <td>--full-download bool</td><td>回追檔案</td><td>下載直播時，嘗試回追已過片段</td>
  </tr>
  <tr>
    <td>--threads-limit int</td><td>多線程數量</td><td>最多同時下載多少m3u8檔案，一般不需要設定</td>
  </tr>
  <tr>
    <td>--referer "str"</td><td>請求網址</td><td>直接下載m3u8時使用</td>
  </tr>
  <tr>
    <td>--user-agent "str"</td><td>標頭</td><td>直接下載m3u8時使用</td>
  </tr>
  <tr>
    <td>--account "str"</td><td>帳號</td><td>用於網站模組自動登入用</td>
  </tr>
  <tr>
    <td>--password "str"</td><td>密碼</td><td>用於網站模組自動登入用</td>
  </tr>
  <tr>
    <td>--chrome-path "str"</td><td>瀏覽器路徑</td><td>Selenium用，一般不需要更改</td>
  </tr>
  <tr>
    <td>--headless bool</td><td>無頭模式</td><td>隱藏瀏覽器視窗，通常搭配網站模組使用</td>
  </tr>
  <tr>
    <td>--skip-media bool</td><td>跳過下載m3u8</td><td>啟用後不下載m3u8連結</td>
  </tr>
  <tr>
    <td>--attachment bool</td><td>下載附件</td><td>搭配網站模組使用，下載m3u8之外的附件</td>
  </tr>
  <tr>
    <td>--twitter_keywords "[str1,str2,str3...]"</td><td>推特m3u8關鍵字</td><td>用於推特模組使用，自動篩選關鍵字</td>
  </tr>
  <tr>
    <td>--skip_urls "[str1,str2,str3...]"</td><td>跳過網址</td><td>輸入欲跳過的m3u8網址</td>
  </tr>
</table>
