import tkinter as tk
from tkinter import ttk
import threading
from functools import partial
from transposer_core import download_and_transpose

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
    
    # 在背景執行緒執行下載和轉調
    def work():
        try:
            def progress_callback(value, msg):
                root.after(0, partial(update_progress, value, msg))
            
            download_and_transpose(url, semitones, progress_callback)
            # 成功完成
            root.after(0, lambda: start_btn.config(state=tk.NORMAL))
        except Exception as e:
            root.after(0, partial(update_progress, 0, "處理失敗，請檢查連結是否正確"))
            root.after(0, lambda: start_btn.config(state=tk.NORMAL))
    
    thread = threading.Thread(target=work)
    thread.daemon = True
    thread.start()

def decrease_semitones():
    """減少半音數"""
    try:
        current = int(semi_entry.get())
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, str(current - 1))
    except:
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, "-1")

def increase_semitones():
    """增加半音數"""
    try:
        current = int(semi_entry.get())
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, str(current + 1))
    except:
        semi_entry.delete(0, tk.END)
        semi_entry.insert(0, "1")

root = tk.Tk()
root.title("YouTube 音檔轉調工具")
root.geometry("420x250")

tk.Label(root, text="YouTube 連結：").pack()
url_entry = tk.Entry(root, width=55)
url_entry.pack()

tk.Label(root, text="升/降半音數（正升負降）：").pack()

# 半音數調整框架
semitones_frame = tk.Frame(root)
semitones_frame.pack()

# 減號按鈕
decrease_btn = tk.Button(semitones_frame, text="-", width=3, command=decrease_semitones)
decrease_btn.pack(side=tk.LEFT, padx=2)

# 半音數輸入框
semi_entry = tk.Entry(semitones_frame, width=10, justify=tk.CENTER)
semi_entry.insert(0, "0")
semi_entry.pack(side=tk.LEFT, padx=2)

# 加號按鈕
increase_btn = tk.Button(semitones_frame, text="+", width=3, command=increase_semitones)
increase_btn.pack(side=tk.LEFT, padx=2)

start_btn = tk.Button(root, text="開始轉調", command=run)
start_btn.pack(pady=15)

# 進度條
progress_bar = ttk.Progressbar(root, length=350, mode='determinate')
progress_bar.pack(pady=5)

# 狀態標籤
status_label = tk.Label(root, text="", fg="blue")
status_label.pack()

root.mainloop()

