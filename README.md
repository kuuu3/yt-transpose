# YouTube 轉調工具

一個用於下載 YouTube 影片的音訊並進行音調轉換的工具。

##  專案結構

```
yt_transpose/
├── app.py              # 主程式（GUI 介面）
├── transposer_core.py  # 核心邏輯（yt-dlp 輸出音訊 + SoundTouch CLI 音調轉換）
├── setup_env.py        # 自動安裝環境（下載依賴）
├── transposer.py       # 命令列單首轉調
├── batch_transpose.py  # 批次處理
├── urls.txt            # 批次檔案（多個連結）
├── requirements.txt    # Python 套件
├── run.bat             # Windows 一鍵啟動（呼叫 run.vbs）
├── run.vbs             # VBScript 啟動腳本（無視窗）
├── soundstretch.exe    # SoundTouch CLI（自動下載）
└── downloads/          # 音檔輸出目錄
```

##  快速開始

### Windows 使用者

直接雙擊 **`run.bat`** 即可啟動 GUI 介面！

### 首次安裝

執行自動安裝腳本（會自動下載並安裝所有依賴）：

```bash
python setup_env.py
```

此腳本會自動：
-  檢查 `imageio-ffmpeg`（用於音訊格式轉換，自動管理，無需手動下載）
-  自動下載 `soundstretch.exe`（從官方網站）- 用於高品質音調轉換

**如果自動下載失敗**，請手動下載：

1. 訪問：https://www.surina.net/soundtouch/download.html
2. 下載 **SoundStretch 2.3.3 for Windows**
3. 解壓縮並找到 `soundstretch.exe`
4. 將 `soundstretch.exe` 複製到專案目錄

**注意**：
- 首次執行時需要網路連線以下載依賴
- `imageio-ffmpeg` 會在安裝時自動下載 ffmpeg，無需手動管理
- 只有 `soundstretch.exe` 會下載到專案目錄

###  GUI 圖形介面

```bash
python app.py
```

開啟圖形介面，輸入 YouTube 連結，選擇處理模式（BPM / rate / tempo + pitch）即可使用。

###  命令列單首轉調

```bash
python transposer.py <YouTube_URL> <半音數>
```

**範例：**
- 降 5 個半音：`python transposer.py "https://youtu.be/RVA_Le5AJtk" -5`
- 升 2 個半音：`python transposer.py "https://youtu.be/xxxx" 2`

###  批次處理

編輯 `urls.txt` 檔案，每行一個連結和半音數：

```
https://youtu.be/abc123  -3
https://youtu.be/xyz789   2
```

執行批次處理：

```bash
python batch_transpose.py
```

##  說明

### 功能特點

- **音調調整（Pitch）**：使用半音數（正數升調，負數降調）
- **速度調整（Tempo）**：改變播放速度，不影響音調（範圍：-95% 到 +5000%）
- **速度與音調同步調整（Rate）**：同時改變速度和音調（範圍：-95% 到 +5000%）
- **BPM 自動調整**：檢測並自動調整到指定 BPM
- **輸出檔案**：根據處理模式自動命名（例如：`原標題_bpm120.mp3`、`原標題_rate-10.0.mp3`、`原標題_pitch+2_tempo20.0.mp3`）
- **存放位置**：預設為 Windows Downloads 資料夾，可在 GUI 中自訂
- **音調轉換**：使用 **SoundTouch CLI** (`soundstretch`) 進行高品質音調轉換

### 處理模式說明

在 GUI 中可選擇三種處理模式（互斥，優先級：BPM > rate > tempo + pitch）：

1. **BPM 模式**：輸入目標 BPM 值，系統會自動檢測原曲 BPM 並調整到指定值
   - 範例：輸入 `120` → 自動調整到 120 BPM

2. **Rate 模式**：同時改變速度和音調
   - 範圍：-95% 到 +5000%
   - 範例：輸入 `-10` → 速度降低 10%，音調也降低
   - 用途：快速同步調整速度和音調

3. **Tempo + Pitch 模式（預設）**：
   - **Tempo**：只改變播放速度，不影響音調（範圍：-95% 到 +5000%）
     - 範例：輸入 `20` → 速度增加 20%，音調保持不變
   - **Pitch**：只改變音調，不影響速度（通過半音數調整）
     - 可同時使用或單獨使用

### 依賴工具

1. **imageio-ffmpeg**（Python 套件，自動管理）
   - **用途**：音訊格式轉換
   - **優勢**：輕量且自動管理，無需手動下載 ffmpeg.exe
   - **原因**：
     - yt-dlp 下載的是 MP3 格式
     - soundstretch 只支援 WAV 格式
     - 需要 ffmpeg 在 MP3 和 WAV 之間轉換
   - **處理流程**：`MP3 → WAV → soundstretch 處理 → WAV → MP3`

2. **soundstretch.exe**（自動下載）
   - **用途**：高品質音調轉換
   - **來源**：從官方網站 https://www.surina.net/soundtouch/ 自動下載

## 許可證

MIT License

