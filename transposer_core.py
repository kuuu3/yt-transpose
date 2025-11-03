import subprocess, os, re, shutil, sys, tempfile

# Windows 上隱藏 subprocess 視窗的輔助函數
def get_subprocess_kwargs():
    """獲取用於隱藏 subprocess 視窗的參數（僅 Windows）"""
    kwargs = {}
    if sys.platform == 'win32':
        # 在 Windows 上使用 CREATE_NO_WINDOW 標誌隱藏 CMD 視窗
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs

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
            timeout=5,
            **get_subprocess_kwargs()
        )
        # 如果有輸出（說明或錯誤），表示命令存在
        if len(result.stdout) > 0 or len(result.stderr) > 0:
            return True
        # 如果沒有輸出，嘗試不帶參數執行
        result = subprocess.run(
            [st],
            capture_output=True, text=True, encoding='utf-8', errors='ignore',
            timeout=5,
            **get_subprocess_kwargs()
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
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
        **get_subprocess_kwargs()
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
    # 在打包環境中，直接使用 yt_dlp 的 Python API，避免通過 subprocess 調用 sys.executable
    # 因為打包後的 sys.executable 指向 exe，會導致啟動新的應用程式視窗
    try:
        import yt_dlp
        use_python_api = True
    except ImportError:
        use_python_api = False
        # 如果無法導入 yt_dlp，嘗試通過命令列調用
        if getattr(sys, 'frozen', False):
            # 打包環境：嘗試查找系統中的 yt-dlp 或 yt_dlp
            yt_dlp_cmd = shutil.which('yt-dlp') or shutil.which('yt_dlp')
            if yt_dlp_cmd:
                yt = [yt_dlp_cmd]
            else:
                # 最後備選：使用 Python（需要系統安裝 Python）
                import shutil as sh
                python_cmd = shutil.which('python') or shutil.which('py')
                if python_cmd:
                    yt = [python_cmd, "-m", "yt_dlp"]
                else:
                    raise Exception("無法找到 yt-dlp。請確保已安裝 yt-dlp：pip install yt-dlp")
        else:
            # 開發環境：使用 Python 模組模式
            yt = [sys.executable, "-m", "yt_dlp"]
    
    ff = get_ffmpeg()
    
    if not ff: 
        raise Exception("ffmpeg not found. Please install imageio-ffmpeg: pip install imageio-ffmpeg")
    
    # 獲取標題
    if progress_callback:
        progress_callback(0, "Getting video title...")
    
    if use_python_api:
        # 使用 Python API 獲取標題
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
    else:
        # 使用命令列獲取標題
        title = subprocess.run([*yt, "--get-title", url], capture_output=True, text=True, **get_subprocess_kwargs()).stdout.strip()
    
    title = sanitize_filename(title)
    
    # 決定輸出目錄
    if output_dir is None:
        output_dir = get_default_output_dir()
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 創建臨時工作目錄，所有操作都在這裡進行
    temp_work_dir = tempfile.mkdtemp(prefix='yt_transpose_')
    
    # 初始化返回路徑，避免在 finally 區塊中未定義
    result_path = None
    
    try:
        # 決定是否需要處理和輸出檔案名稱
        # 只有當參數不是預設值時才需要處理
        # 正規化 semitones：確保接近零的值不被視為需要處理
        normalized_semitones = round(float(semitones), 2) if semitones != 0 else 0.0
        if abs(normalized_semitones) < 0.01:
            normalized_semitones = 0.0
        
        needs_processing = (
            normalized_semitones != 0 or 
            (tempo is not None and tempo != 0.0) or 
            (rate is not None and rate != 0.0) or 
            (bpm is not None and bpm != 120)
        )
        
        # 生成描述性的檔案名稱，根據實際調整的參數
        parts = []
        
        if needs_processing:
            # BPM 模式：只顯示 BPM
            if bpm is not None:
                parts.append(f"bpm{bpm:.0f}")
            
            # Rate 模式：只顯示 Rate
            elif rate is not None:
                parts.append(f"rate{rate:+.1f}")
            
            # 預設模式：顯示 transpose 和 tempo（根據實際值）
            else:
                # 使用正規化後的 semitones
                if normalized_semitones != 0:
                    # 如果是整數，不顯示小數點；如果是浮點數，顯示最多兩位小數
                    if normalized_semitones == int(normalized_semitones):
                        parts.append(f"transpose{int(normalized_semitones):+}")
                    else:
                        parts.append(f"transpose{normalized_semitones:+.2f}")
                if tempo is not None and tempo != 0.0:
                    parts.append(f"tempo{tempo:+.1f}")
        
        # 臨時工作目錄中的檔案路徑
        temp_input_path = os.path.join(temp_work_dir, f"{title}.mp3")
        
        # 臨時工作目錄中的輸出檔案路徑（處理後的檔案）
        if parts:
            temp_output_path = os.path.join(temp_work_dir, f"{title}_{'_'.join(parts)}.mp3")
        else:
            temp_output_path = temp_input_path  # 沒有處理，輸出和輸入相同
        
        # 最終輸出到目標資料夾的路徑
        if parts:
            final_output_path = os.path.join(output_dir, f"{title}_{'_'.join(parts)}.mp3")
        else:
            final_output_path = os.path.join(output_dir, f"{title}.mp3")
        
        # 下載檔案到臨時目錄
        was_downloaded = False
        # 下載（確保 yt-dlp 能找到 ffmpeg）
        if progress_callback:
            progress_callback(30, f"Downloading: {title}")
        print(f"Downloading: {title}")
        
        # 下載音訊
        if use_python_api:
            # 使用 Python API 下載（避免在打包環境中調用 sys.executable）
            # 輸出模板：去掉 .mp3 擴展名，yt-dlp 會自動添加
            output_template = temp_input_path.rsplit('.', 1)[0]  # 移除 .mp3
            
            # 統一下載為 MP3 格式
            ydl_opts = {
                'format': 'bestaudio/best',  # 選擇最佳音訊格式
                'outtmpl': output_template + '.%(ext)s',
                'postprocessors': [],
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [],
            }
            
            # 統一轉換為 MP3（需要 ffmpeg）
            if ff:
                ffmpeg_dir = os.path.dirname(os.path.abspath(ff))
                ffprobe_name = 'ffprobe.exe' if sys.platform == 'win32' else 'ffprobe'
                ffprobe_path = os.path.join(ffmpeg_dir, ffprobe_name)
                
                # 如果找到 ffprobe，使用後處理器自動轉換為 MP3
                if os.path.exists(ffprobe_path):
                    # 有 ffprobe，使用 FFmpegExtractAudio 後處理器自動轉換為 MP3
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                    ydl_opts['ffmpeg_location'] = ffmpeg_dir
                else:
                    # 沒有 ffprobe，yt-dlp 無法自動轉換
                    # 下載後手動使用 ffmpeg 轉換為 MP3
                    ydl_opts['ffmpeg_location'] = ffmpeg_dir
            else:
                raise Exception("ffmpeg not found. Cannot convert to MP3 format.")
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # 查找下載的檔案（統一為 MP3 格式）
                downloaded_file = None
                
                # 方法1：檢查預期路徑（應該是 MP3）
                base_name = os.path.splitext(output_template)[0]
                
                # 如果有使用後處理器，應該已經是 MP3
                if len(ydl_opts.get('postprocessors', [])) > 0:
                    # 使用後處理器，直接檢查 MP3
                    test_path = f"{base_name}.mp3"
                    if os.path.exists(test_path):
                        downloaded_file = test_path
                else:
                    # 沒有使用後處理器，需要檢查可能的格式
                    possible_extensions = ['mp3', 'm4a', 'webm', 'opus', 'ogg', 'mp4', 'flac']
                    for ext in possible_extensions:
                        test_path = f"{base_name}.{ext}"
                        if os.path.exists(test_path):
                            downloaded_file = test_path
                            break
                
                # 方法2：檢查預期路徑（完整路徑）
                if not downloaded_file and os.path.exists(temp_input_path):
                    downloaded_file = temp_input_path
                
                # 方法3：搜尋臨時工作目錄（優先找 MP3）
                if not downloaded_file:
                    try:
                        temp_dir_files = os.listdir(temp_work_dir)
                        # 優先查找 MP3，然後查找其他音訊格式
                        audio_files = []
                        mp3_files = []
                        for filename in temp_dir_files:
                            file_path = os.path.join(temp_work_dir, filename)
                            if os.path.isfile(file_path):
                                ext = os.path.splitext(filename)[1].lower().lstrip('.')
                                if ext == 'mp3':
                                    mp3_files.append((file_path, os.path.getmtime(file_path)))
                                elif ext in ['m4a', 'webm', 'opus', 'ogg', 'mp4', 'flac']:
                                    audio_files.append((file_path, os.path.getmtime(file_path)))
                        
                        # 優先選擇 MP3，然後選擇其他格式中最新的
                        if mp3_files:
                            mp3_files.sort(key=lambda x: x[1], reverse=True)
                            downloaded_file = mp3_files[0][0]
                        elif audio_files:
                            audio_files.sort(key=lambda x: x[1], reverse=True)
                            downloaded_file = audio_files[0][0]
                    except Exception as e:
                        pass
                
                if not downloaded_file:
                    debug_info = f"搜尋位置: {base_name}, {temp_input_path}, {temp_work_dir}"
                    raise Exception(f"無法找到下載的檔案。{debug_info}")
                
                # 如果下載的不是 MP3，需要手動轉換為 MP3
                needs_conversion = not downloaded_file.endswith('.mp3')
                
                if needs_conversion:
                    if progress_callback:
                        progress_callback(40, "Converting to MP3...")
                    
                    # 使用 ffmpeg 轉換為 MP3
                    convert_cmd = [
                        ff,
                        "-i", downloaded_file,
                        "-codec:a", "libmp3lame",
                        "-q:a", "2",  # 高品質
                        "-y",  # 覆蓋輸出檔案
                        temp_input_path
                    ]
                    result = subprocess.run(convert_cmd, capture_output=True, text=True, **get_subprocess_kwargs())
                    
                    if result.returncode != 0:
                        raise Exception(f"轉換為 MP3 失敗: {result.stderr}")
                    
                    # 刪除原始檔案
                    try:
                        os.remove(downloaded_file)
                    except:
                        pass
                    downloaded_file = temp_input_path
                
                # 確保最終檔案名稱正確（在臨時目錄中）
                if downloaded_file != temp_input_path:
                    if os.path.exists(temp_input_path):
                        try:
                            os.remove(temp_input_path)
                        except:
                            pass
                    try:
                        os.rename(downloaded_file, temp_input_path)
                    except:
                        # 如果重命名失敗，複製檔案
                        shutil.copy2(downloaded_file, temp_input_path)
                        try:
                            os.remove(downloaded_file)
                        except:
                            pass
                
                was_downloaded = True
            except Exception as e:
                raise Exception(f"Download failed: {str(e)}")
        else:
            # 使用命令列下載到臨時目錄
            yt_cmd = [*yt, "-x", "--audio-format", "mp3", "-o", temp_input_path]
            
            # 如果找到 ffmpeg，告訴 yt-dlp 它的位置
            if ff:
                yt_cmd.extend(["--ffmpeg-location", ff])
            
            result = subprocess.run(yt_cmd + [url], capture_output=True, text=True, **get_subprocess_kwargs())
            if result.returncode != 0:
                raise Exception(f"Download failed: {result.stderr}")
            was_downloaded = True
    
        # 如果需要處理（轉調、速度調整等）
        if needs_processing:
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
                    # 使用正規化後的 semitones
                    if normalized_semitones != 0:
                        msg_parts.append(f"Transpose {normalized_semitones:+} semitones")
                    if tempo is not None:
                        msg_parts.append(f"Tempo {tempo:+.1f}%")
                    msg = ", ".join(msg_parts) if msg_parts else "Processing"
                    progress_callback(70, f"{msg} (using SoundTouch CLI)")
                    print(f"{msg} (using SoundTouch CLI)")
            
            # soundstretch 需要 WAV 格式，使用臨時檔案（在臨時工作目錄中）
            temp_wav_input = os.path.join(temp_work_dir, "temp_input.wav")
            temp_wav_output = os.path.join(temp_work_dir, "temp_output.wav")
            
            try:
                # 將 MP3 轉換為 WAV（soundstretch 需要）
                if progress_callback:
                    progress_callback(75, "Converting to WAV format...")
                convert_cmd = [
                    ff,
                    "-i", temp_input_path,
                    "-y",  # 覆蓋輸出檔案
                    "-acodec", "pcm_s16le",  # 16-bit PCM
                    temp_wav_input
                ]
                result = subprocess.run(convert_cmd, capture_output=True, text=True, **get_subprocess_kwargs())
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
                
                # 添加處理參數（按優先級：BPM > rate > tempo + transpose）
                # 注意：BPM 和 rate 模式也會支援 pitch 調整
                if bpm is not None:
                    # BPM 模式：檢測並調整到指定 BPM
                    soundstretch_cmd.append(f"-bpm={bpm}")
                    # BPM 模式下也支援 pitch 調整（使用正規化後的 semitones）
                    if normalized_semitones != 0:
                        soundstretch_cmd.append(f"-pitch={normalized_semitones:.2f}")
                elif rate is not None:
                    # Rate 模式：同時改變速度和音調
                    soundstretch_cmd.append(f"-rate={rate:.2f}")
                    # Rate 模式下也支援額外的 pitch 調整（使用正規化後的 semitones）
                    if normalized_semitones != 0:
                        soundstretch_cmd.append(f"-pitch={normalized_semitones:.2f}")
                else:
                    # 預設模式：分別控制 transpose 和 tempo
                    # 使用正規化後的 semitones
                    if normalized_semitones != 0:
                        soundstretch_cmd.append(f"-pitch={normalized_semitones:.2f}")
                    if tempo is not None:
                        soundstretch_cmd.append(f"-tempo={tempo:.2f}")
                
                result = subprocess.run(soundstretch_cmd, capture_output=True, text=True, **get_subprocess_kwargs())
                if result.returncode != 0:
                    raise Exception(f"SoundTouch processing failed: {result.stderr}")
                
                # 將 WAV 轉換回 MP3（在臨時工作目錄中）
                if progress_callback:
                    progress_callback(90, "Converting back to MP3...")
                convert_back_cmd = [
                    ff,
                    "-i", temp_wav_output,
                    "-q:a", "2",  # 高品質 MP3 編碼
                    "-y",
                    temp_output_path
                ]
                result = subprocess.run(convert_back_cmd, capture_output=True, text=True, **get_subprocess_kwargs())
                if result.returncode != 0:
                    raise Exception(f"Failed to convert WAV to MP3: {result.stderr}")
                
            finally:
                # 清理臨時 WAV 檔案
                for temp_file in [temp_wav_input, temp_wav_output]:
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except OSError:
                            pass
        
        # 所有操作完成後，將最終檔案從臨時目錄複製到目標目錄
        if progress_callback:
            progress_callback(95, "Moving files to output directory...")
        
        final_input_path = os.path.join(output_dir, f"{title}.mp3")
        
        # 如果有處理，只複製處理後的檔案；如果沒有處理，複製原始檔案
        if needs_processing and os.path.exists(temp_output_path):
            # 有處理：只複製處理後的檔案
            if os.path.exists(final_output_path):
                try:
                    os.remove(final_output_path)
                except OSError:
                    pass
            # 複製處理後的檔案到目標目錄
            shutil.copy2(temp_output_path, final_output_path)
            # 不複製原始檔案（只需要處理後的版本）
        else:
            # 沒有處理：複製原始檔案
            if os.path.exists(temp_input_path):
                if os.path.exists(final_input_path):
                    try:
                        os.remove(final_input_path)
                    except OSError:
                        pass
                # 複製原始檔案到目標目錄
                shutil.copy2(temp_input_path, final_input_path)
        
        # 確定最終返回的路徑
        if needs_processing:
            result_path = final_output_path
        else:
            result_path = final_input_path
        
    finally:
        # 清理臨時工作目錄
        try:
            shutil.rmtree(temp_work_dir)
        except Exception:
            pass
    
    # 完成（在 finally 之後，確保 result_path 已定義）
    if result_path is None:
        # 如果發生錯誤導致 result_path 未定義，使用預設路徑（不帶處理參數）
        result_path = os.path.join(output_dir, f"{title}.mp3")
    
    if progress_callback:
        progress_callback(100, "Completed!")
    print(f"\nCompleted: {result_path}")
    return result_path

