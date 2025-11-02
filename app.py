import tkinter as tk
from tkinter import ttk, filedialog
import threading
from functools import partial
import os
import json
from transposer_core import download_and_transpose, get_default_output_dir

# 配置文件路徑
CONFIG_FILE = "config.json"

def load_config():
    """載入設定"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"output_dir": get_default_output_dir()}

def save_config(config):
    """儲存設定"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

def select_output_dir():
    """選擇輸出目錄"""
    current_dir = output_dir_entry.get().strip()
    if not current_dir:
        current_dir = get_default_output_dir()
    
    dir_path = filedialog.askdirectory(
        title="選擇輸出目錄",
        initialdir=current_dir
    )
    if dir_path:
        output_dir_entry.config(state='normal')
        output_dir_entry.delete(0, tk.END)
        output_dir_entry.insert(0, dir_path)
        output_dir_entry.config(state='readonly')
        # 更新配置
        config = load_config()
        config["output_dir"] = dir_path
        save_config(config)

def update_progress(value, message):
    """更新進度條和狀態訊息"""
    progress_bar['value'] = value
    status_label.config(text=message)
    root.update_idletasks()

def run():
    url = url_entry.get().strip()
    try:
        semitones = int(semi_entry.get())
    except:
        update_progress(0, "錯誤: 半音數必須是整數")
        return
    
    if not url:
        update_progress(0, "請輸入 YouTube 連結")
        return
    
    # 禁用按鈕，防止重複點擊
    start_btn.config(state=tk.DISABLED)
    progress_bar['value'] = 0
    status_label.config(text="")
    
    # 取得輸出目錄
    output_dir = output_dir_entry.get().strip()
    if not output_dir:
        output_dir = get_default_output_dir()
    
    # 在背景執行緒執行下載和轉調
    def work():
        try:
            def progress_callback(value, msg):
                root.after(0, partial(update_progress, value, msg))
            
            download_and_transpose(url, semitones, progress_callback, output_dir)
            # 成功完成
            root.after(0, lambda: start_btn.config(state=tk.NORMAL))
            root.after(0, lambda: status_label.config(text=f"完成！檔案已儲存至：{output_dir}"))
        except Exception as e:
            root.after(0, partial(update_progress, 0, f"處理失敗：{str(e)}"))
            root.after(0, lambda: start_btn.config(state=tk.NORMAL))
    
    thread = threading.Thread(target=work)
    thread.daemon = True
    thread.start()

def decrease_semitones():
    """減少半音數"""
    try:
        current = int(semi_entry.get())
        semi_entry.config(state='normal')
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, str(current - 1))
        semi_entry.config(state='readonly')
    except:
        semi_entry.config(state='normal')
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, "-1")
        semi_entry.config(state='readonly')

def increase_semitones():
    """增加半音數"""
    try:
        current = int(semi_entry.get())
        semi_entry.config(state='normal')
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, str(current + 1))
        semi_entry.config(state='readonly')
    except:
        semi_entry.config(state='normal')
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, "1")
        semi_entry.config(state='readonly')

root = tk.Tk()
root.title("YouTube 音檔轉調工具")
root.geometry("500x320")

# 載入設定
config = load_config()
default_output_dir = config.get("output_dir", get_default_output_dir())

tk.Label(root, text="YouTube 連結：").pack()
url_entry = tk.Entry(root, width=60)
url_entry.pack()

tk.Label(root, text="升/降半音數（正升負降）：").pack()

# 半音數調整框架
semitones_frame = tk.Frame(root)
semitones_frame.pack()

# 減號按鈕
decrease_btn = tk.Button(semitones_frame, text="-", width=3, command=decrease_semitones)
decrease_btn.pack(side=tk.LEFT, padx=2)

# 半音數輸入框（只讀，只能通過按鈕調整）
semi_entry = tk.Entry(semitones_frame, width=10, justify=tk.CENTER)
semi_entry.insert(0, "0")
semi_entry.config(state='readonly')
semi_entry.pack(side=tk.LEFT, padx=2)

# 加號按鈕
increase_btn = tk.Button(semitones_frame, text="+", width=3, command=increase_semitones)
increase_btn.pack(side=tk.LEFT, padx=2)

# 輸出目錄設定
output_dir_frame = tk.Frame(root)
output_dir_frame.pack(pady=10)

tk.Label(output_dir_frame, text="輸出目錄：").pack(side=tk.LEFT)

# 輸出目錄輸入框（只讀，只能通過瀏覽按鈕選擇）
output_dir_entry = tk.Entry(output_dir_frame, width=40)
output_dir_entry.insert(0, default_output_dir)
output_dir_entry.config(state='readonly')
output_dir_entry.pack(side=tk.LEFT, padx=5)

browse_btn = tk.Button(output_dir_frame, text="瀏覽...", command=select_output_dir)
browse_btn.pack(side=tk.LEFT)

start_btn = tk.Button(root, text="開始轉調", command=run)
start_btn.pack(pady=15)

# 進度條
progress_bar = ttk.Progressbar(root, length=350, mode='determinate')
progress_bar.pack(pady=5)

# 狀態標籤
status_label = tk.Label(root, text="", fg="blue")
status_label.pack()

root.mainloop()

