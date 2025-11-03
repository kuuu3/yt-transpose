import flet as ft
import threading
import queue
import os
import logging
import tkinter as tk
from tkinter import filedialog
from transposer_core import download_and_transpose, get_default_output_dir

# 顏色方案（與 app.py 保持一致）
COLORS = {
    'bg': '#2b2b2b',
    'fg': '#ffffff',
    'frame_bg': '#3c3c3c',
    'entry_bg': '#1e1e1e',
    'entry_fg': '#ffffff',
    'accent': '#4a9eff',
    'accent_hover': '#5aaeff',
    'success': '#4caf50',
    'danger': '#f44336',
    'text_muted': '#b0b0b0',
    'border': '#555555',
}

def main(page: ft.Page):
    page.title = "YouTube 音檔轉調工具"
    page.window.width = 380
    page.window.height = 680
    page.window.resizable = False
    page.window.center()
    page.bgcolor = COLORS['bg']
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.update()
    
    # 使用預設輸出目錄
    default_output_dir = get_default_output_dir()
    
    # 創建更新隊列（用於線程安全的 UI 更新）
    update_queue = queue.Queue()
    
    # 處理隊列中的更新請求
    def process_updates():
        try:
            while True:
                update_func = update_queue.get_nowait()
                update_func()
        except queue.Empty:
            pass
        try:
            page.update()
        except AssertionError:
            # Flet 要求在主線程中更新，這個錯誤是預期的
            pass
        except Exception as e:
            # 記錄其他意外的錯誤
            logging.error(f"更新頁面時發生錯誤: {e}", exc_info=True)
    
    # 使用定時器定期處理更新隊列
    update_timer_running = False
    
    def schedule_update():
        nonlocal update_timer_running
        if not update_timer_running:
            return
        process_updates()
        # 使用 threading.Timer 定期檢查更新隊列（每 100ms）
        threading.Timer(0.1, schedule_update).start()
    
    def start_update_timer():
        nonlocal update_timer_running
        if not update_timer_running:
            update_timer_running = True
            schedule_update()
    
    def stop_update_timer():
        nonlocal update_timer_running
        update_timer_running = False
    
    # 輔助函數：在主線程中執行 UI 更新
    def invoke_on_main_thread(update_func):
        """在主線程中執行 UI 更新函數，優先使用 Flet 的 API，否則使用隊列機制"""
        if hasattr(page, 'invoke_later'):
            page.invoke_later(update_func)
        elif hasattr(page, 'call_later'):
            page.call_later(0.0, update_func)
        else:
            # 備選方案：使用隊列機制
            update_queue.put(update_func)
            start_update_timer()
    
    # 全局 tkinter 根視窗（用於文件對話框，避免重複創建）
    tk_root = None
    
    # 控制變數
    transpose_value = 0
    pitch_value = 0.0
    speed_value = 0.0
    speed_mode = "tempo"  # tempo, rate, bpm
    
    # UI 元件
    url_field = ft.TextField(
        label="YouTube 連結",
        hint_text="請輸入 YouTube 連結",
        expand=True,
        height=40,
        text_size=10,
        bgcolor=COLORS['entry_bg'],
        color=COLORS['entry_fg'],
        border_color=COLORS['border'],
        focused_border_color=COLORS['accent'],
    )
    
    transpose_value_text = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=COLORS['accent'])
    transpose_slider = ft.Slider(
        min=-24,
        max=24,
        divisions=48,
        value=0,
        expand=True,
        active_color=COLORS['accent'],
        inactive_color=COLORS['entry_bg'],
    )
    transpose_scale_var = {"value": transpose_slider}
    
    def on_transpose_change(e):
        update_transpose(e.control.value, transpose_value_text, transpose_scale_var)
    
    transpose_slider.on_change = on_transpose_change
    
    pitch_value_text = ft.Text("0.00", size=20, weight=ft.FontWeight.BOLD, color=COLORS['accent'])
    pitch_freq_text = ft.Text("440.0 Hz", size=9, color=COLORS['text_muted'])
    pitch_slider = ft.Slider(
        min=-12.0,
        max=12.0,
        divisions=2400,  # 提高精度到 0.01 半音（1 cent）
        value=0.0,
        expand=True,
        active_color=COLORS['accent'],
        inactive_color=COLORS['entry_bg'],
    )
    
    def on_pitch_change(e):
        update_pitch(e.control.value, pitch_value_text, pitch_freq_text)
    
    pitch_slider.on_change = on_pitch_change
    
    speed_value_text = ft.Text("0.0", size=20, weight=ft.FontWeight.BOLD, color=COLORS['accent'])
    speed_mode_dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option("tempo", "(Tempo)"),
            ft.dropdown.Option("rate", "(Rate)"),
            ft.dropdown.Option("bpm", "(BPM)"),
        ],
        value="tempo",
        width=115,
        text_size=12,
        bgcolor=COLORS['entry_bg'],
        color=COLORS['fg'],
        border_color=COLORS['border'],
        focused_border_color=COLORS['accent'],
    )
    speed_unit_text = ft.Text("%", size=9, color=COLORS['text_muted'])
    speed_slider = ft.Slider(
        min=-95,
        max=500,
        divisions=595,
        value=0.0,
        expand=True,
        active_color=COLORS['accent'],
        inactive_color=COLORS['entry_bg'],
    )
    
    def on_speed_change(e):
        update_speed(e.control.value, speed_value_text, speed_unit_text, speed_mode)
    
    speed_slider.on_change = on_speed_change
    
    output_dir_field = ft.TextField(
        label="輸出目錄",
        value=default_output_dir,
        read_only=True,
        expand=True,
        height=40,
        text_size=9,
        bgcolor=COLORS['entry_bg'],
        color=COLORS['entry_fg'],
        border_color=COLORS['border'],
        focused_border_color=COLORS['accent'],
    )
    
    progress_bar = ft.ProgressBar(value=0, color=COLORS['accent'], bgcolor=COLORS['frame_bg'])
    status_text = ft.Text("", size=9, color=COLORS['text_muted'])
    start_button = ft.ElevatedButton(
        text="開始下載",
        bgcolor=COLORS['success'],
        color=COLORS['fg'],
        width=280,
        height=45,
        on_click=lambda e: start_process(),
    )
    
    def update_transpose(value, value_text, scale_var):
        nonlocal transpose_value
        transpose_value = round(value)
        value_text.value = str(transpose_value)
        try:
            page.update()
        except AssertionError:
            # Flet 要求在主線程中更新，這個錯誤是預期的
            pass
        except Exception as e:
            # 記錄其他意外的錯誤
            logging.error(f"更新 transpose 時發生錯誤: {e}", exc_info=True)
    
    def update_pitch(value, value_text, freq_text):
        nonlocal pitch_value
        # 正規化pitch值：四捨五入到2位小數，並將接近零的值設為零
        raw_value = float(value)
        pitch_value = round(raw_value, 2)
        # 如果值非常接近零（小於0.01），設為零以避免不必要的處理
        if abs(pitch_value) < 0.01:
            pitch_value = 0.0
        value_text.value = f"{pitch_value:.2f}"  # 顯示 2 位小數（0.01 半音精度）
        # 計算對應的頻率（以 A4=440Hz 為基準）
        freq = 440.0 * (2 ** (pitch_value / 12))
        freq_text.value = f"{freq:.2f} Hz"  # 頻率也顯示 2 位小數以反映更精確的調整
        try:
            page.update()
        except AssertionError:
            # Flet 要求在主線程中更新，這個錯誤是預期的
            pass
        except Exception as e:
            # 記錄其他意外的錯誤
            logging.error(f"更新 pitch 時發生錯誤: {e}", exc_info=True)
    
    def update_speed(value, value_text, unit_text, mode):
        nonlocal speed_value, speed_mode
        raw_value = float(value)
        speed_mode = speed_mode_dropdown.value
        
        # 正規化 speed 值，避免浮點數精度問題
        if mode == "bpm":
            # BPM 模式：四捨五入為整數
            speed_value = round(raw_value)
            value_text.value = f"{int(speed_value)}"  # 使用 int() 確保顯示為整數
            unit_text.value = "bpm"
        else:
            # Tempo/Rate 模式：四捨五入到1位小數，接近零的值設為零
            speed_value = round(raw_value, 1)
            if abs(speed_value) < 0.1:
                speed_value = 0.0
            value_text.value = f"{speed_value:.1f}"
            unit_text.value = "%"
        try:
            page.update()
        except AssertionError:
            # Flet 要求在主線程中更新，這個錯誤是預期的
            pass
        except Exception as e:
            # 記錄其他意外的錯誤
            logging.error(f"更新 speed 時發生錯誤: {e}", exc_info=True)
    
    def change_speed_mode():
        nonlocal speed_value, speed_mode
        speed_mode = speed_mode_dropdown.value
        
        if speed_mode == "bpm":
            speed_slider.min = 60
            speed_slider.max = 200
            speed_slider.divisions = 140
            speed_slider.value = 120
            speed_value = 120
            speed_value_text.value = "120"
            speed_unit_text.value = "bpm"
        elif speed_mode == "rate":
            speed_slider.min = -95
            speed_slider.max = 500
            speed_slider.divisions = 595
            speed_slider.value = 0.0
            speed_value = 0.0
            speed_value_text.value = "0.0"
            speed_unit_text.value = "%"
        else:  # tempo
            speed_slider.min = -95
            speed_slider.max = 500
            speed_slider.divisions = 595
            speed_slider.value = 0.0
            speed_value = 0.0
            speed_value_text.value = "0.0"
            speed_unit_text.value = "%"
        
        page.update()
    
    speed_mode_dropdown.on_change = lambda e: change_speed_mode()
    
    def reset_transpose():
        nonlocal transpose_value
        transpose_slider.value = 0
        transpose_value = 0
        transpose_value_text.value = "0"
        try:
            page.update()
        except AssertionError:
            # Flet 要求在主線程中更新，這個錯誤是預期的
            pass
        except Exception as e:
            # 記錄其他意外的錯誤
            logging.error(f"重置 transpose 時發生錯誤: {e}", exc_info=True)
    
    def reset_pitch():
        nonlocal pitch_value
        pitch_slider.value = 0.0
        pitch_value = 0.0
        pitch_value_text.value = "0.00"
        pitch_freq_text.value = "440.0 Hz"
        try:
            page.update()
        except AssertionError:
            # Flet 要求在主線程中更新，這個錯誤是預期的
            pass
        except Exception as e:
            # 記錄其他意外的錯誤
            logging.error(f"重置 pitch 時發生錯誤: {e}", exc_info=True)
    
    def reset_speed():
        nonlocal speed_value
        mode = speed_mode_dropdown.value
        if mode == "bpm":
            speed_slider.value = 120
            speed_value = 120
            speed_value_text.value = "120"
            speed_unit_text.value = "bpm"
        else:
            speed_slider.value = 0.0
            speed_value = 0.0
            speed_value_text.value = "0.0"
            speed_unit_text.value = "%"
        try:
            page.update()
        except AssertionError:
            # Flet 要求在主線程中更新，這個錯誤是預期的
            pass
        except Exception as e:
            # 記錄其他意外的錯誤
            logging.error(f"重置 speed 時發生錯誤: {e}", exc_info=True)
    
    def start_process():
        url = url_field.value.strip()
        if not url:
            status_text.value = "請輸入 YouTube 連結"
            status_text.color = COLORS['danger']
            page.update()
            return
        
        # 禁用按鈕
        start_button.disabled = True
        start_button.bgcolor = '#888888'
        progress_bar.value = 0
        status_text.value = ""
        page.update()
        
        # 取得輸出目錄
        output_dir = output_dir_field.value.strip()
        if not output_dir:
            output_dir = get_default_output_dir()
            output_dir_field.value = output_dir
        
        # 取得處理參數（優先使用 pitch，如果為 0 則使用 transpose）
        # 正規化 pitch 值：確保接近零的值被設為零
        normalized_pitch = round(float(pitch_value), 2)
        if abs(normalized_pitch) < 0.01:
            normalized_pitch = 0.0
        
        # 正規化 transpose 值：使用 round 而不是 int，避免截斷問題
        normalized_transpose = round(float(transpose_slider.value))
        
        # 如果 pitch 有設定（不為零），使用 pitch；否則使用 transpose
        if normalized_pitch != 0.0:
            semitones = normalized_pitch
        else:
            semitones = float(normalized_transpose)
        tempo_val = None
        rate_val = None
        bpm_val = None
        
        # 根據 Speed 模式決定參數（只有當值不是預設值時才傳遞）
        mode = speed_mode_dropdown.value
        if mode == "bpm":
            # 正規化 BPM 值：四捨五入為整數，避免浮點數精度問題
            bpm_value = round(float(speed_slider.value))
            if bpm_value != 120:  # 預設值是 120
                bpm_val = float(bpm_value)
        elif mode == "rate":
            # 正規化 rate 值：四捨五入到1位小數，接近零的值設為零
            rate_value = round(float(speed_slider.value), 1)
            if abs(rate_value) < 0.1:  # 接近零的值設為零
                rate_value = 0.0
            if rate_value != 0.0:  # 預設值是 0.0
                rate_val = rate_value
        else:  # tempo
            # 正規化 tempo 值：四捨五入到1位小數，接近零的值設為零
            tempo_value = round(float(speed_slider.value), 1)
            if abs(tempo_value) < 0.1:  # 接近零的值設為零
                tempo_value = 0.0
            if tempo_value != 0.0:  # 預設值是 0.0
                tempo_val = tempo_value
        
        # 在背景執行緒執行下載和轉調
        def work():
            try:
                def progress_callback(value, msg):
                    def update_ui():
                        try:
                            progress_bar.value = value / 100.0
                            status_text.value = msg
                            status_text.color = COLORS['text_muted']
                            page.update()
                        except AssertionError:
                            # Flet 要求在主線程中更新，這個錯誤是預期的
                            pass
                        except Exception as e:
                            # 記錄其他意外的錯誤
                            logging.error(f"更新進度時發生錯誤: {e}", exc_info=True)
                    
                    # 使用輔助函數在主線程執行更新
                    invoke_on_main_thread(update_ui)
                
                download_and_transpose(url, semitones, progress_callback, output_dir, tempo_val, rate_val, bpm_val)
                # 成功完成
                def update_success():
                    try:
                        start_button.disabled = False
                        start_button.bgcolor = COLORS['success']
                        status_text.value = f"完成！檔案已儲存至：{output_dir}"
                        status_text.color = COLORS['success']
                        page.update()
                    except AssertionError:
                        # Flet 要求在主線程中更新，這個錯誤是預期的
                        pass
                    except Exception as e:
                        # 記錄其他意外的錯誤
                        logging.error(f"更新成功狀態時發生錯誤: {e}", exc_info=True)
                
                # 使用輔助函數在主線程執行更新
                invoke_on_main_thread(update_success)
            except Exception as e:
                # 記錄錯誤
                logging.error(f"下載處理失敗: {e}", exc_info=True)
                
                def update_error():
                    try:
                        progress_bar.value = 0
                        start_button.disabled = False
                        start_button.bgcolor = COLORS['success']
                        status_text.value = f"錯誤：{str(e)}"
                        status_text.color = COLORS['danger']
                        page.update()
                    except AssertionError:
                        # Flet 要求在主線程中更新，這個錯誤是預期的
                        pass
                    except Exception as update_err:
                        # 記錄其他意外的錯誤
                        logging.error(f"更新錯誤狀態時發生錯誤: {update_err}", exc_info=True)
                
                # 使用輔助函數在主線程執行更新
                invoke_on_main_thread(update_error)
        
        thread = threading.Thread(target=work)
        thread.daemon = True
        thread.start()
    
    # 創建控制區塊的輔助函數
    def create_control_card(title, value_widget, slider, reset_func, minus_btn=None, plus_btn=None):
        header = ft.Row([
            ft.Text(title, size=11, weight=ft.FontWeight.BOLD, color=COLORS['fg'], expand=True),
            value_widget,
            ft.TextButton(
                text="↻",
                tooltip="重置",
                on_click=lambda e: reset_func(),
                style=ft.ButtonStyle(color=COLORS['text_muted']),
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        # 將按鈕放在滑桿左右兩側
        slider_row = ft.Row([
            minus_btn if minus_btn else ft.Container(width=20),
            slider,
            plus_btn if plus_btn else ft.Container(width=20),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
        
        controls = [header, slider_row]
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column(controls, tight=True, spacing=4),
                padding=8,
                bgcolor=COLORS['frame_bg'],
            ),
            elevation=0,
            color=COLORS['border'],
        )
    
    # Transpose 控制區塊
    def transpose_minus_click(e):
        new_value = max(-24, transpose_slider.value - 1)
        transpose_slider.value = new_value
        update_transpose(new_value, transpose_value_text, transpose_scale_var)
    
    def transpose_plus_click(e):
        new_value = min(24, transpose_slider.value + 1)
        transpose_slider.value = new_value
        update_transpose(new_value, transpose_value_text, transpose_scale_var)
    
    transpose_minus_btn = ft.TextButton(
        text="−",
        on_click=transpose_minus_click,
        style=ft.ButtonStyle(color=COLORS['fg']),
        width=25,
    )
    transpose_plus_btn = ft.TextButton(
        text="+",
        on_click=transpose_plus_click,
        style=ft.ButtonStyle(color=COLORS['fg']),
        width=25,
    )
    
    transpose_card = create_control_card(
        "Transpose",
        transpose_value_text,
        transpose_slider,
        reset_transpose,
        transpose_minus_btn,
        transpose_plus_btn,
    )
    
    # Pitch 控制區塊
    pitch_header_widget = ft.Row([
        ft.Text("Pitch", size=11, weight=ft.FontWeight.BOLD, color=COLORS['fg'], expand=True),
        pitch_freq_text,
        pitch_value_text,
        ft.TextButton(
            text="↻",
            tooltip="重置",
            on_click=lambda e: reset_pitch(),
            style=ft.ButtonStyle(color=COLORS['text_muted']),
        ),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    def pitch_minus_click(e):
        new_value = max(-12.0, round(pitch_slider.value - 0.01, 2))  # 每次調整 0.01 半音
        pitch_slider.value = new_value
        update_pitch(new_value, pitch_value_text, pitch_freq_text)
    
    def pitch_plus_click(e):
        new_value = min(12.0, round(pitch_slider.value + 0.01, 2))  # 每次調整 0.01 半音
        pitch_slider.value = new_value
        update_pitch(new_value, pitch_value_text, pitch_freq_text)
    
    pitch_minus_btn = ft.TextButton(
        text="−",
        on_click=pitch_minus_click,
        style=ft.ButtonStyle(color=COLORS['fg']),
        width=25,
    )
    pitch_plus_btn = ft.TextButton(
        text="+",
        on_click=pitch_plus_click,
        style=ft.ButtonStyle(color=COLORS['fg']),
        width=25,
    )
    
    pitch_slider_row = ft.Row([
        pitch_minus_btn,
        pitch_slider,
        pitch_plus_btn,
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
    
    pitch_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                pitch_header_widget,
                pitch_slider_row,
            ], tight=True, spacing=4),
            padding=8,
            bgcolor=COLORS['frame_bg'],
        ),
        elevation=0,
        color=COLORS['border'],
    )
    
    # Speed 控制區塊
    speed_header_widget = ft.Row([
        ft.Text("Speed", size=11, weight=ft.FontWeight.BOLD, color=COLORS['fg']),
        speed_mode_dropdown,
        ft.Row([
            speed_unit_text,
            speed_value_text,
        ], spacing=3, tight=True),
        ft.TextButton(
            text="↻",
            tooltip="重置",
            on_click=lambda e: reset_speed(),
            style=ft.ButtonStyle(color=COLORS['text_muted']),
        ),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=5)
    
    def speed_minus_click(e):
        new_value = max(speed_slider.min, speed_slider.value - 1)
        speed_slider.value = new_value
        update_speed(new_value, speed_value_text, speed_unit_text, speed_mode_dropdown.value)
    
    def speed_plus_click(e):
        new_value = min(speed_slider.max, speed_slider.value + 1)
        speed_slider.value = new_value
        update_speed(new_value, speed_value_text, speed_unit_text, speed_mode_dropdown.value)
    
    speed_minus_btn = ft.TextButton(
        text="−",
        on_click=speed_minus_click,
        style=ft.ButtonStyle(color=COLORS['fg']),
        width=25,
    )
    speed_plus_btn = ft.TextButton(
        text="+",
        on_click=speed_plus_click,
        style=ft.ButtonStyle(color=COLORS['fg']),
        width=25,
    )
    
    speed_slider_row = ft.Row([
        speed_minus_btn,
        speed_slider,
        speed_plus_btn,
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
    
    speed_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                speed_header_widget,
                speed_slider_row,
            ], tight=True, spacing=4),
            padding=8,
            bgcolor=COLORS['frame_bg'],
        ),
        elevation=0,
        color=COLORS['border'],
    )
    
    # 瀏覽按鈕 - 選擇目錄
    def browse_output_dir(e):
        # 使用 tkinter 的文件對話框選擇目錄
        nonlocal tk_root
        try:
            # 只在需要時創建 tkinter 根視窗
            if tk_root is None:
                tk_root = tk.Tk()
                tk_root.withdraw()  # 隱藏主視窗
                tk_root.attributes('-topmost', False)  # 不置頂，避免干擾
            
            # 獲取當前輸出目錄作為初始目錄
            initial_dir = output_dir_field.value
            if not initial_dir or not os.path.exists(initial_dir):
                initial_dir = get_default_output_dir()
            
            # 打開目錄選擇對話框
            selected_dir = filedialog.askdirectory(
                title="選擇輸出目錄",
                initialdir=initial_dir,
                parent=tk_root
            )
            
            if selected_dir:
                output_dir_field.value = selected_dir
                status_text.value = f"已設定輸出目錄：{selected_dir}"
                status_text.color = COLORS['success']
                page.update()
        except Exception as ex:
            status_text.value = f"選擇目錄時發生錯誤：{str(ex)}"
            status_text.color = COLORS['danger']
            page.update()
        finally:
            # 確保視窗被正確處理
            if tk_root:
                try:
                    tk_root.update_idletasks()
                except Exception as e:
                    # 記錄 tkinter 更新錯誤
                    logging.error(f"更新 tkinter 視窗時發生錯誤: {e}", exc_info=True)
    
    browse_btn = ft.ElevatedButton(
        text="瀏覽",
        bgcolor=COLORS['entry_bg'],
        color=COLORS['fg'],
        width=60,
        height=40,
        on_click=browse_output_dir,
    )
    
    # 輸出目錄行
    output_dir_row = ft.Row([
        output_dir_field,
        browse_btn,
    ], expand=True)
    
    # 組裝頁面
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("YouTube 音檔轉調工具", size=16, weight=ft.FontWeight.BOLD, color=COLORS['fg']),
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=10, horizontal=5),
                ),
                ft.Container(
                    content=url_field,
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                ),
                ft.Container(
                    content=ft.Column([
                        transpose_card,
                        pitch_card,
                        speed_card,
                    ], spacing=8, tight=True),
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("", size=10, color=COLORS['fg']),
                        output_dir_row,
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                ),
                ft.Container(
                    content=start_button,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=8, horizontal=5),
                ),
                ft.Container(
                    content=ft.Column([
                        progress_bar,
                        status_text,
                    ], spacing=3, tight=True),
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                ),
            ], spacing=0, tight=True, scroll=ft.ScrollMode.HIDDEN),
            expand=True,
        ),
    )

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP, port=0)
