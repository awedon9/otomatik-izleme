import tkinter as tk
import pyautogui
import pytesseract
import pygame
from pynput import keyboard
import threading
import time
import os
import sys

# 🔧 Tesseract yolunu ayarla (gömülü ya da dış)
def get_tesseract_path():
    if getattr(sys, 'frozen', False):  # exe içindeyse
        return os.path.join(sys._MEIPASS, "tesseract", "tesseract.exe")
    else:
        return os.path.abspath("tesseract/tesseract.exe")

pytesseract.pytesseract_cmd = get_tesseract_path()

# 🔊 Ses dosyasını bulma
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller için
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Global değişkenler
click_position = None
ocr_region = None
target_keywords = []
is_running = False
listener = None

def select_click_position():
    def on_click(x, y):
        global click_position
        click_position = (x, y)
        print("🖱️ Tıklama konumu:", click_position)
        pos_window.destroy()

    pos_window = tk.Toplevel()
    pos_window.attributes("-fullscreen", True)
    pos_window.attributes("-alpha", 0.3)
    pos_window.configure(bg='black')
    pos_window.bind("<Button-1>", lambda e: on_click(e.x_root, e.y_root))

def select_ocr_region():
    global ocr_region
    region = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
    selecting = {"started": False}

    def start_select(event):
        region["x1"], region["y1"] = event.x, event.y
        selecting["started"] = True

    def update_select(event):
        if selecting["started"]:
            canvas.coords(rect, region["x1"], region["y1"], event.x, event.y)

    def finish_select(event):
        region["x2"], region["y2"] = event.x, event.y
        selecting["started"] = False
        x1, y1 = region["x1"], region["y1"]
        x2, y2 = region["x2"], region["y2"]
        ocr_x = min(x1, x2)
        ocr_y = min(y1, y2)
        ocr_w = abs(x2 - x1)
        ocr_h = abs(y2 - y1)
        global ocr_region
        ocr_region = (ocr_x, ocr_y, ocr_w, ocr_h)
        print("📷 OCR alanı:", ocr_region)
        root.destroy()

    root = tk.Toplevel()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    canvas = tk.Canvas(root, bg='black')
    canvas.pack(fill=tk.BOTH, expand=True)
    rect = canvas.create_rectangle(0, 0, 0, 0, outline="red", width=2)
    canvas.bind("<Button-1>", start_select)
    canvas.bind("<B1-Motion>", update_select)
    canvas.bind("<ButtonRelease-1>", finish_select)

def toggle_monitoring(label, entry):
    global is_running, target_keywords
    if not click_position or not ocr_region:
        label.config(text="⚠️ Önce tıklama ve OCR alanı seç.")
        return

    if not is_running:
        raw_input = entry.get().strip().lower()
        if not raw_input:
            label.config(text="⚠️ Aranacak metni gir.")
            return
        target_keywords = [w.strip() for w in raw_input.split(",") if w.strip()]
        is_running = True
        label.config(text="🟢 İzleme: AÇIK (TAB ile durdur)")
        threading.Thread(target=click_loop, daemon=True).start()
        threading.Thread(target=ocr_loop, daemon=True).start()
    else:
        is_running = False
        label.config(text="🔴 İzleme: DURDU (TAB ile başlat)")

def click_loop():
    while is_running:
        if click_position:
            pyautogui.click(click_position)
            print("🖱️ Tıklandı:", click_position)
        time.sleep(5)

def ocr_loop():
    last_text = ""
    while is_running:
        if ocr_region:
            screenshot = pyautogui.screenshot(region=ocr_region)
            text = pytesseract.image_to_string(screenshot).lower().strip()
            if text != last_text:
                print("🧠 OCR:", text)
                last_text = text
            for kelime in target_keywords:
                if kelime in text:
                    print("✅ Metin bulundu:", kelime)
                    try:
                        pygame.mixer.init()
                        pygame.mixer.music.load(resource_path("ding.mp3"))
                        pygame.mixer.music.play()
                    except Exception as e:
                        print("Ses çalma hatası:", e)
                    break
        time.sleep(3)

def listen_for_tab(label, entry):
    def on_press(key):
        if key == keyboard.Key.tab:
            toggle_monitoring(label, entry)

    global listener
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

# 🎨 GUI Arayüz
app = tk.Tk()
app.title("Randevu İzleme Sistemi")
app.geometry("420x360")
app.configure(bg="#e6e6e6")

tk.Label(app, text="📍 Randevu İzleme Uygulaması", font=("Helvetica", 16, "bold"), bg="#e6e6e6").pack(pady=10)
tk.Button(app, text="1. Tıklama Noktası Seç", font=("Arial", 11), width=30, command=select_click_position).pack(pady=5)
tk.Button(app, text="2. OCR Alanı Seç", font=("Arial", 11), width=30, command=select_ocr_region).pack(pady=5)

tk.Label(app, text="3. Aranacak Metin(ler) (virgülle):", bg="#e6e6e6").pack(pady=5)
entry = tk.Entry(app, font=("Arial", 11), width=35)
entry.pack(pady=5)

status = tk.Label(app, text="Durum: Hazır", font=("Arial", 11, "italic"), fg="blue", bg="#e6e6e6")
status.pack(pady=10)

tk.Button(app, text="4. Başlat / Durdur", font=("Arial", 11), bg="#4CAF50", fg="white",
          command=lambda: toggle_monitoring(status, entry)).pack(pady=5)

tk.Label(app, text="💡 TAB tuşuna basarak da izlemeyi kontrol edebilirsin.",
         font=("Arial", 9), bg="#e6e6e6", fg="gray").pack(pady=10)

# Başlat
listen_for_tab(status, entry)
pygame.init()
app.mainloop()
