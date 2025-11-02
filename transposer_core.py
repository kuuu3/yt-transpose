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
    """取得 ffmpeg 執行檔路徑，優先使用 imageio-ffmpeg 下載的版本"""
    # 先檢查本地目錄
    ff = find_exec("ffmpeg")
    if ff:
        return ff
    
    # 嘗試使用 imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        return ff
    except ImportError:
        pass
    
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

def download_and_transpose(url, semitones, progress_callback=None):
    # yt-dlp 改用 Python 模組模式執行
    yt = [sys.executable, "-m", "yt_dlp"]
    ff = get_ffmpeg()
    
    if not ff: 
        raise Exception("ffmpeg not found, please run python setup_env.py first")
    
    # 獲取標題
    if progress_callback:
        progress_callback(0, "Getting video title...")
    title = subprocess.run([*yt, "--get-title", url], capture_output=True, text=True).stdout.strip()
    title = sanitize_filename(title)
    
    os.makedirs("downloads", exist_ok=True)
    
    # 需要轉調的情況
    input_path = f"downloads/{title}.mp3"
    
    if semitones == 0:
        # 沒有調整音高，直接下載原版就好
        output_path = input_path
    else:
        # 需要轉調
        output_path = f"downloads/{title}_transpose_{semitones:+}.mp3"
    
    # 檢查是否已有原檔存在，記錄是否需要刪除原檔
    was_downloaded = False
    if not os.path.exists(input_path):
        # 下載
        if progress_callback:
            progress_callback(30, f"Downloading: {title}")
        print(f"Downloading: {title}")
        result = subprocess.run([*yt, "-x", "--audio-format", "mp3", "-o", input_path, url], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Download failed: {result.stderr}")
        was_downloaded = True
    
    # 如果需要轉調
    if semitones != 0:
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
        
        # 轉調 - 使用 SoundTouch CLI (soundstretch)
        if progress_callback:
            progress_callback(70, f"Transposing: {semitones:+} semitones (using SoundTouch CLI)")
        print(f"Transposing: {semitones:+} semitones (using SoundTouch CLI)")
        
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
            
            # 使用 soundstretch 進行音調轉換
            if progress_callback:
                progress_callback(80, "Processing with SoundTouch...")
            soundstretch_cmd = [
                soundstretch,
                temp_wav_input,
                temp_wav_output,
                f"-pitch={semitones:.2f}"
            ]
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

