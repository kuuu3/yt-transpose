import subprocess, os, re, shutil, sys, tempfile

def sanitize_filename(name): 
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_base_path():
    """取得基礎路徑，支援 PyInstaller 打包後的路徑"""
    if getattr(sys, 'frozen', False):
        # 如果是打包後的執行檔，使用執行檔所在目錄
        return os.path.dirname(sys.executable)
    else:
        # 開發環境，使用腳本所在目錄
        return os.path.dirname(os.path.abspath(__file__))

def find_exec(name):
    """查找可執行檔案，支援 PyInstaller 打包"""
    base_path = get_base_path()
    
    # 先檢查本地目錄（打包後的執行檔目錄或腳本目錄）
    local_path = os.path.join(base_path, f"{name}.exe")
    if os.path.exists(local_path):
        return local_path
    
    # 如果是打包後的執行檔，也檢查 _MEIPASS（臨時解壓目錄）
    if getattr(sys, 'frozen', False):
        try:
            meipass_path = os.path.join(sys._MEIPASS, f"{name}.exe")
            if os.path.exists(meipass_path):
                return meipass_path
        except:
            pass
    
    # 檢查系統 PATH
    path = shutil.which(name)
    if path: 
        return path
    
    # 檢查 Windows Store Python 的安裝路徑
    home = os.path.expanduser("~")
    alt = os.path.join(home, "AppData", "Local", "Packages",
                       "PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0",
                       "LocalCache", "local-packages", "Python311", "Scripts", f"{name}.exe")
    return alt if os.path.exists(alt) else None

def get_ffmpeg():
    """取得 ffmpeg 執行檔路徑，優先使用 imageio-ffmpeg（輕量且自動管理）"""
    # 優先使用 imageio-ffmpeg（自動管理，無需手動下載）
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        if ff:
            return ff
    except ImportError:
        pass
    
    # 備選：檢查本地目錄
    ff = find_exec("ffmpeg")
    if ff:
        return ff
    
    # 備選：檢查系統 PATH
    path = shutil.which("ffmpeg")
    if path:
        return path
    
    return None

def get_soundstretch():
    """取得 soundstretch 執行檔路徑"""
    # 在 Windows 上可能是 soundstretch.exe
    st = find_exec("soundstretch")
    if st:
        return st
    return None

def check_soundstretch_available():
    """檢查 soundstretch 是否可用"""
    st = get_soundstretch()
    if not st:
        return False
    try:
        # 嘗試執行 soundstretch --help 或直接執行（通常會顯示使用說明）
        result = subprocess.run(
            [st, "--help"],
            capture_output=True, text=True, encoding='utf-8', errors='ignore',
            timeout=5
        )
        # 如果有輸出（說明或錯誤），表示命令存在
        if len(result.stdout) > 0 or len(result.stderr) > 0:
            return True
        # 如果沒有輸出，嘗試不帶參數執行
        result = subprocess.run(
            [st],
            capture_output=True, text=True, encoding='utf-8', errors='ignore',
            timeout=5
        )
        return len(result.stdout) > 0 or len(result.stderr) > 0
    except:
        return False

def get_samplerate(path):
    """取得音訊檔案的取樣率"""
    ff = get_ffmpeg()
    if not ff:
        # 如果找不到 ffmpeg，預設使用 48000
        return 48000
    
    # 使用 ffmpeg 讀取檔案資訊
    result = subprocess.run(
        [ff, "-i", path, "-hide_banner"],
        capture_output=True, text=True, encoding='utf-8', errors='ignore'
    )
    # 從錯誤訊息中提取採樣率（ffmpeg 會在 stderr 中顯示資訊）
    if result.stderr:
        match = re.search(r'(\d+)\s+Hz', result.stderr)
        if match:
            return int(match.group(1))
    # 如果偵測失敗，預設使用 48000
    return 48000

def get_default_output_dir():
    """取得預設輸出目錄（Windows Downloads 資料夾）"""
    try:
        # 獲取 Windows Downloads 資料夾路徑
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads_path):
            return downloads_path
        # 如果 Downloads 不存在，回退到當前目錄的 downloads 資料夾
        return os.path.join(os.getcwd(), "downloads")
    except:
        # 如果出錯，使用當前目錄的 downloads 資料夾
        return os.path.join(os.getcwd(), "downloads")

def download_and_transpose(url, semitones, progress_callback=None, output_dir=None, tempo=None, rate=None, bpm=None):
    # yt-dlp 改用 Python 模組模式執行
    yt = [sys.executable, "-m", "yt_dlp"]
    ff = get_ffmpeg()
    
    if not ff: 
        raise Exception("ffmpeg not found. Please install imageio-ffmpeg: pip install imageio-ffmpeg")
    
    # 獲取標題
    if progress_callback:
        progress_callback(0, "Getting video title...")
    title = subprocess.run([*yt, "--get-title", url], capture_output=True, text=True).stdout.strip()
    title = sanitize_filename(title)
    
    # 決定輸出目錄
    if output_dir is None:
        output_dir = get_default_output_dir()
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 輸入檔案路徑
    input_path = os.path.join(output_dir, f"{title}.mp3")
    
    # 決定是否需要處理和輸出檔案名稱
    # 只有當參數不是預設值時才需要處理
    needs_processing = (
        semitones != 0 or 
        (tempo is not None and tempo != 0.0) or 
        (rate is not None and rate != 0.0) or 
        (bpm is not None and bpm != 120)
    )
    
    if needs_processing:
        # 生成描述性的檔案名稱
        parts = []
        if bpm is not None:
            parts.append(f"bpm{bpm:.0f}")
        elif rate is not None:
            parts.append(f"rate{rate:+.1f}")
        else:
            if semitones != 0:
                parts.append(f"pitch{semitones:+}")
            if tempo is not None:
                parts.append(f"tempo{tempo:+.1f}")
        
        if parts:
            output_path = os.path.join(output_dir, f"{title}_{'_'.join(parts)}.mp3")
        else:
            output_path = input_path
    else:
        # 沒有處理，直接使用原始檔名
        output_path = input_path
    
    # 檢查是否已有原檔存在，記錄是否需要刪除原檔
    was_downloaded = False
    if not os.path.exists(input_path):
        # 下載（確保 yt-dlp 能找到 ffmpeg）
        if progress_callback:
            progress_callback(30, f"Downloading: {title}")
        print(f"Downloading: {title}")
        
        # 構建 yt-dlp 命令，指定 ffmpeg 位置
        yt_cmd = [*yt, "-x", "--audio-format", "mp3", "-o", input_path]
        
        # 如果找到 ffmpeg，告訴 yt-dlp 它的位置
        # --ffmpeg-location 可以接受目錄或執行檔路徑
        if ff:
            # 直接指定 ffmpeg 執行檔路徑（yt-dlp 會自動找同目錄的 ffprobe，如果沒有就只使用 ffmpeg）
            yt_cmd.extend(["--ffmpeg-location", ff])
        
        result = subprocess.run(yt_cmd + [url], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Download failed: {result.stderr}")
        was_downloaded = True
    
    # 如果需要處理（轉調、速度調整等）
    needs_processing = (semitones != 0 or tempo is not None or rate is not None or bpm is not None)
    if needs_processing:
        # 刪除已存在的輸出檔案
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        
        # 檢查 soundstretch 是否可用
        if not check_soundstretch_available():
            local_dir = os.path.dirname(os.path.abspath(__file__))
            error_msg = (
                "soundstretch CLI 未找到！\n\n"
                "請安裝 SoundTouch CLI 工具：\n"
                "1. 從以下網址下載：\n"
                "   - https://www.surina.net/soundtouch/download.html\n"
                "   - 或 https://github.com/SoundTouch/SoundTouch/releases\n\n"
                f"2. 解壓縮後，將 'soundstretch.exe' 複製到此目錄：\n"
                f"   {local_dir}\n\n"
                "3. 或者將 soundstretch 加入到系統 PATH\n\n"
                "執行 'python setup_env.py' 可檢查安裝狀態。"
            )
            raise Exception(error_msg)
        
        soundstretch = get_soundstretch()
        
        # 處理 - 使用 SoundTouch CLI (soundstretch)
        if progress_callback:
            if bpm is not None:
                progress_callback(70, f"Processing: Adjusting to {bpm} BPM (using SoundTouch CLI)")
                print(f"Processing: Adjusting to {bpm} BPM (using SoundTouch CLI)")
            elif rate is not None:
                progress_callback(70, f"Processing: Rate {rate:+.1f}% (using SoundTouch CLI)")
                print(f"Processing: Rate {rate:+.1f}% (using SoundTouch CLI)")
            else:
                msg_parts = []
                if semitones != 0:
                    msg_parts.append(f"Pitch {semitones:+} semitones")
                if tempo is not None:
                    msg_parts.append(f"Tempo {tempo:+.1f}%")
                msg = ", ".join(msg_parts) if msg_parts else "Processing"
                progress_callback(70, f"{msg} (using SoundTouch CLI)")
                print(f"{msg} (using SoundTouch CLI)")
        
        # soundstretch 需要 WAV 格式，使用臨時檔案（系統臨時目錄，處理完自動清理）
        temp_wav_input = None
        temp_wav_output = None
        
        try:
            # 創建臨時 WAV 輸入檔案（在系統臨時目錄）
            temp_wav_input_fd, temp_wav_input = tempfile.mkstemp(
                suffix='.wav',
                dir=tempfile.gettempdir()
            )
            os.close(temp_wav_input_fd)  # 關閉檔案句柄，讓外部程序可以寫入
            
            # 創建臨時 WAV 輸出檔案（在系統臨時目錄）
            temp_wav_output_fd, temp_wav_output = tempfile.mkstemp(
                suffix='.wav',
                dir=tempfile.gettempdir()
            )
            os.close(temp_wav_output_fd)  # 關閉檔案句柄，讓外部程序可以寫入
            
            # 將 MP3 轉換為 WAV（soundstretch 需要）
            if progress_callback:
                progress_callback(75, "Converting to WAV format...")
            convert_cmd = [
                ff,
                "-i", input_path,
                "-y",  # 覆蓋輸出檔案
                "-acodec", "pcm_s16le",  # 16-bit PCM
                temp_wav_input
            ]
            result = subprocess.run(convert_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to convert MP3 to WAV: {result.stderr}")
            
            # 使用 soundstretch 進行音調轉換和處理
            if progress_callback:
                progress_callback(80, "Processing with SoundTouch...")
            
            # 構建 soundstretch 命令參數
            soundstretch_cmd = [
                soundstretch,
                temp_wav_input,
                temp_wav_output
            ]
            
            # 添加處理參數（按優先級：BPM > rate > tempo + pitch）
            if bpm is not None:
                # BPM 模式：檢測並調整到指定 BPM
                soundstretch_cmd.append(f"-bpm={bpm}")
            elif rate is not None:
                # Rate 模式：同時改變速度和音調
                soundstretch_cmd.append(f"-rate={rate:.2f}")
            else:
                # 預設模式：分別控制 pitch 和 tempo
                if semitones != 0:
                    soundstretch_cmd.append(f"-pitch={semitones:.2f}")
                if tempo is not None:
                    soundstretch_cmd.append(f"-tempo={tempo:.2f}")
            
            result = subprocess.run(soundstretch_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"SoundTouch processing failed: {result.stderr}")
            
            # 將 WAV 轉換回 MP3（最終輸出）
            if progress_callback:
                progress_callback(90, "Converting back to MP3...")
            convert_back_cmd = [
                ff,
                "-i", temp_wav_output,
                "-q:a", "2",  # 高品質 MP3 編碼
                "-y",
                output_path
            ]
            result = subprocess.run(convert_back_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to convert WAV to MP3: {result.stderr}")
            
        finally:
            # 確保清理臨時檔案（即使 NamedTemporaryFile 會自動清理，這裡作為保險）
            for temp_file in [temp_wav_input, temp_wav_output]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except OSError:
                        pass
        
        # 只刪除本次下載的臨時檔案
        if was_downloaded and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except OSError:
                # 檔案被其他程序使用時無法刪除，忽略錯誤
                pass
    
    # 完成
    if progress_callback:
        progress_callback(100, "Completed!")
    print(f"\nCompleted: {output_path}")
    return output_path

