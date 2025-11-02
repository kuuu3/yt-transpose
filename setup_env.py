import subprocess, os, shutil, sys
import urllib.request
import zipfile
import tempfile

# Check and auto-download ffmpeg
local_dir = os.path.dirname(os.path.abspath(__file__))
local_ffmpeg = os.path.join(local_dir, "ffmpeg.exe")
local_soundstretch = os.path.join(local_dir, "soundstretch.exe")

def download_soundstretch():
    """自動下載 soundstretch.exe"""
    print("正在下載 soundstretch.exe...")
    
    temp_dir = tempfile.mkdtemp()
    download_url = "https://www.surina.net/soundtouch/soundstretch-v2.3.3.zip"
    
    try:
        print(f"正在從官方網站下載: {download_url}")
        zip_path = os.path.join(temp_dir, "soundtouch.zip")
        
        # 下載 ZIP 檔案
        urllib.request.urlretrieve(download_url, zip_path)
        
        # 解壓縮
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 查找 soundstretch.exe（不區分大小寫）
            for file_info in zip_ref.filelist:
                filename_lower = file_info.filename.lower()
                if 'soundstretch.exe' in filename_lower:
                    # 解壓到臨時目錄
                    zip_ref.extract(file_info.filename, temp_dir)
                    extracted_path = os.path.join(temp_dir, file_info.filename)
                    
                    # 複製到目標目錄
                    if os.path.exists(extracted_path):
                        shutil.copy2(extracted_path, local_soundstretch)
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        print("[OK] soundstretch.exe downloaded successfully")
                        return True
        
        # 如果沒找到 soundstretch.exe
        print("[ERROR] ZIP 檔案中找不到 soundstretch.exe")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
        
    except Exception as e:
        print(f"下載失敗: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

# Check and setup ffmpeg
if os.path.exists(local_ffmpeg):
    print("[OK] ffmpeg found in local directory")
else:
    # Check system ffmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        if result.returncode == 0:
            print("[OK] System ffmpeg found")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        # Need to download ffmpeg
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            
            # Copy ffmpeg to local directory
            try:
                shutil.copy2(ffmpeg_path, local_ffmpeg)
                print("[OK] ffmpeg copied to local directory")
            except Exception:
                print("[OK] Using imageio-ffmpeg's ffmpeg")
        except Exception:
            print("[WARNING] Could not setup ffmpeg automatically")

# Check and setup soundstretch
if os.path.exists(local_soundstretch):
    print("[OK] soundstretch found in local directory")
else:
    # Check system soundstretch
    try:
        result = subprocess.run(["soundstretch", "--help"], capture_output=True)
        if result.returncode == 0 or len(result.stdout) > 0 or len(result.stderr) > 0:
            print("[OK] System soundstretch found")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print("[WARNING] soundstretch not found in system PATH")
        print("Attempting to download automatically...")
        
        # 嘗試自動下載
        if download_soundstretch():
            if os.path.exists(local_soundstretch):
                print("[OK] soundstretch setup complete")
            else:
                print("\n[ERROR] Download completed but file not found!")
                sys.exit(1)
        else:
            print("\n[ERROR] Automatic download failed!")
            print("\n請手動下載 soundstretch.exe：")
            print("\n方法 1：從 GitHub 下載（推薦）")
            print("  1. 訪問：https://github.com/SoundTouch/SoundTouch/releases")
            print("  2. 下載最新的 Windows 版本的 ZIP 檔案")
            print("  3. 解壓縮並找到 soundstretch.exe")
            print(f"  4. 將 soundstretch.exe 複製到此目錄: {local_dir}")
            print("\n方法 2：從官方網站下載")
            print("  1. 訪問：https://www.surina.net/soundtouch/download.html")
            print("  2. 下載 Windows 版本")
            print(f"  3. 將 soundstretch.exe 複製到此目錄: {local_dir}")
            print("\n方法 3：使用 Chocolatey（如果已安裝）")
            print("  choco install soundtouch")
            print("\n完成後，請重新執行此腳本驗證安裝。")
            
            # 不退出，允許用戶手動下載後繼續
            choice = input("\n是否要繼續（已手動下載 soundstretch.exe）？[y/N]: ")
            if choice.lower() != 'y':
                sys.exit(1)

