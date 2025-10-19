import tkinter as tk
from tkinter import ttk, filedialog
import threading
import pydirectinput
import time
from PIL import ImageGrab
import pytesseract
import requests
import configparser
import os

# ----------------- Tesseract Path -----------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ----------------- Globals -----------------
root = tk.Tk()
root.title("Sol's Popper v4.4")
root.geometry("900x600")

coords = {}
label_dict = {}
potion_vars = {}
potion_loops = {}
notify_vars = {}
running = False
last_detected_biome = None
last_biome_time = {"Pumpkin Moon":0, "Graveyard":0}

WEBHOOK_URL = "https://discord.com/api/webhooks/1361918380998660177/5K3ntB8GqZ8K1PDFWVzTKN3SkbZRMTj_EQn76QYYrrm6gc4-hY64SXa7dGQhobf4n2Z6"

# ----------------- Tabs -----------------
tab_control = ttk.Notebook(root)
macro_tab = ttk.Frame(tab_control)
coords_tab = ttk.Frame(tab_control)
discord_tab = ttk.Frame(tab_control)
config_tab = ttk.Frame(tab_control)

tab_control.add(macro_tab, text='Macro')
tab_control.add(coords_tab, text='Coordinates')
tab_control.add(discord_tab, text='Discord')
tab_control.add(config_tab, text='Configuration')
tab_control.pack(expand=1, fill='both')

# ----------------- Macro Tab -----------------
start_btn = tk.Button(macro_tab, text="Start (F1)")
start_btn.grid(row=0, column=0, padx=10, pady=10)
stop_btn = tk.Button(macro_tab, text="Stop (F2)")
stop_btn.grid(row=0, column=1, padx=10, pady=10)

# ----------------- Coordinates Tab -----------------
def select_area(name):
    selection = {}
    start = {}
    overlay = tk.Toplevel(root)
    overlay.attributes('-fullscreen', True)
    overlay.attributes('-alpha', 0.3)
    overlay.configure(bg='gray')
    canvas = tk.Canvas(overlay, width=overlay.winfo_screenwidth(), height=overlay.winfo_screenheight())
    canvas.pack()
    rect = None

    def on_press(event):
        start['x'] = event.x_root
        start['y'] = event.y_root

    def on_drag(event):
        nonlocal rect
        if rect:
            canvas.delete(rect)
        x0, y0 = start['x'], start['y']
        x1, y1 = event.x_root, event.y_root
        rect = canvas.create_rectangle(x0, y0, x1, y1, outline='red', width=2)

    def on_release(event):
        selection['x'] = min(start['x'], event.x_root)
        selection['y'] = min(start['y'], event.y_root)
        selection['w'] = abs(event.x_root - start['x'])
        selection['h'] = abs(event.y_root - start['y'])
        coords[name] = selection
        label_dict[name].config(text=f"{name}: {selection}")
        overlay.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    overlay.wait_window()

coord_names = ["Middle of Screen", "Inventory", "Search Bar", "First Potion Slot", "Use Button", "Close Inventory"]
for i, name in enumerate(coord_names):
    tk.Label(coords_tab, text=f"{name} Coords:").grid(row=i, column=0, sticky="w", padx=10, pady=5)
    label = tk.Label(coords_tab, text="Not set")
    label.grid(row=i, column=1, sticky="w")
    label_dict[name] = label
    tk.Button(coords_tab, text="Choose", command=lambda n=name: select_area(n)).grid(row=i, column=2, padx=5)

# ----------------- Discord Tab -----------------
tk.Label(discord_tab, text="Discord Webhook:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
webhook_entry = tk.Entry(discord_tab, width=70)
webhook_entry.grid(row=0, column=1, padx=5, pady=5)
webhook_entry.insert(0, WEBHOOK_URL)

tk.Label(discord_tab, text="Only Notify When:").grid(row=1, column=0, sticky="w", padx=10)
notify_biomes = ["Graveyard", "Pumpkin Moon"]
for i, biome in enumerate(notify_biomes):
    var = tk.IntVar(value=1)
    cb = tk.Checkbutton(discord_tab, text=biome, variable=var)
    cb.grid(row=1+i, column=1, sticky="w", padx=5)
    notify_vars[biome] = var

# ----------------- Configuration Tab -----------------
tk.Label(config_tab, text="Choose Potions to use and loops:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
example_potions = ["Heavenly Potion", "Bound Potion", "Fortune Potion"]
for i, potion in enumerate(example_potions):
    var = tk.IntVar()
    potion_vars[potion] = var
    cb = tk.Checkbutton(config_tab, text=potion, variable=var)
    cb.grid(row=i+1, column=0, sticky="w", padx=20)
    loops_entry = tk.Entry(config_tab, width=5)
    loops_entry.grid(row=i+1, column=1, padx=5)
    loops_entry.insert(0,"1")
    potion_loops[potion] = loops_entry

# Save / Load Buttons
def save_macro():
    folder = filedialog.askdirectory(title="Choose folder to save macro")
    if not folder: return
    name = tk.simpledialog.askstring("Save Macro","Enter filename (without .ini):")
    if not name: return
    path = os.path.join(folder,f"{name}.ini")
    config = configparser.ConfigParser()
    config["COORDS"] = {k:str(v) for k,v in coords.items()}
    config["POTIONS"] = {p:str(potion_vars[p].get())+","+potion_loops[p].get() for p in potion_vars}
    config["DISCORD"] = {"webhook": webhook_entry.get()}
    config["NOTIFY"] = {b:str(notify_vars[b].get()) for b in notify_vars}
    with open(path,"w") as f:
        config.write(f)

def load_macro():
    path = tk.filedialog.askopenfilename(title="Select macro file", filetypes=[("INI files","*.ini")])
    if not path: return
    config = configparser.ConfigParser()
    config.read(path)
    # Load coords
    for k,v in config["COORDS"].items():
        coords[k] = eval(v)
        if k in label_dict:
            label_dict[k].config(text=f"{k}: {coords[k]}")
    # Load potions
    for p,v in config["POTIONS"].items():
        val,loops = v.split(",")
        potion_vars[p].set(int(val))
        potion_loops[p].delete(0,tk.END)
        potion_loops[p].insert(0,loops)
    # Load discord
    webhook_entry.delete(0,tk.END)
    webhook_entry.insert(0,config["DISCORD"].get("webhook",""))
    # Load notify
    for b,v in config["NOTIFY"].items():
        notify_vars[b].set(int(v))

tk.Button(config_tab, text="Save Macro", command=save_macro).grid(row=10, column=0, pady=10)
tk.Button(config_tab, text="Load Macro", command=load_macro).grid(row=10, column=1, pady=10)

# ----------------- Discord Helper -----------------
DISCORD_COLORS = {
    "start": 0x00FF00,
    "stop": 0xFF0000,
    "Pumpkin Moon": 0xFFA500,
    "Graveyard": 0x808080,
    "using": 0x0000FF,
    "used": 0x0000FF
}

def send_discord_message(message,color_key="start"):
    webhook_url = webhook_entry.get().strip()
    if not webhook_url: return
    data = {"embeds":[{"description": message,"color":DISCORD_COLORS.get(color_key,0xFFFFFF)}]}
    try:
        requests.post(webhook_url,json=data)
    except Exception as e:
        print(f"Discord message failed: {e}")

# ----------------- Macro Logic -----------------
def center(area):
    return area['x'] + area.get('w',0)//2, area['y'] + area.get('h',0)//2

BIOME_RECT = {'x':10,'y':840,'w':192,'h':70}
BIOME_VARIANTS = {
    "Graveyard": ["GRAVEYARD","[GRAVEYARD]","GRAVE YARD"],
    "Pumpkin Moon": ["PUMPKIN MOON","[PUMPKIN MOON]","PUMPKINMOON"]
}

def detect_biome(selected_biomes):
    img = ImageGrab.grab(bbox=(BIOME_RECT['x'],BIOME_RECT['y'],BIOME_RECT['x']+BIOME_RECT['w'],BIOME_RECT['y']+BIOME_RECT['h']))
    text = pytesseract.image_to_string(img)
    lines = [line.strip().upper() for line in text.splitlines() if line.strip() and any(c.isalpha() for c in line)]
    for biome in selected_biomes:
        variants_clean = [v.replace("[","").replace("]","").strip().upper() for v in BIOME_VARIANTS.get(biome,[])]
        for line in lines:
            clean_line = line.replace("[","").replace("]","").strip().upper()
            if clean_line in variants_clean:
                return biome
    return None

def wait_or_stop(seconds):
    global running
    for _ in range(seconds):
        if not running:
            return False
        time.sleep(1)
    return True

def start_macro():
    global running
    running=True
    send_discord_message("Macro started!","start")
    threading.Thread(target=macro_loop,daemon=True).start()

def stop_macro():
    global running
    running=False
    send_discord_message("Macro stopped!","stop")

def macro_loop():
    global running,last_detected_biome,last_biome_time
    last_middle_click = 0
    while running:
        mid = coords.get("Middle of Screen")
        selected_biomes = [b for b,var in notify_vars.items() if var.get()]
        detected = detect_biome(selected_biomes)

        current_time = time.time()
        if detected:
            # Ignore if detected within last 2 minutes
            if current_time - last_biome_time.get(detected,0) < 120:
                detected = None
            else:
                last_biome_time[detected] = current_time

        if detected and detected != last_detected_biome:
            color_key = detected
            send_discord_message(f"{detected} Biome Detected!",color_key)
            last_detected_biome = detected

            # Inventory click
            inv = coords.get("Inventory")
            if inv:
                x,y = center(inv)
                pydirectinput.click(x,y)
                time.sleep(0.5)

            # Search Bar
            search = coords.get("Search Bar")
            if search:
                x,y = center(search)
                pydirectinput.click(x,y)
                time.sleep(0.05)
                for potion,var in potion_vars.items():
                    if var.get():
                        pydirectinput.write(potion.lower(),interval=0.05)
                        time.sleep(0.2)
                        break

            # First Potion Slot
            first_slot = coords.get("First Potion Slot")
            if first_slot:
                x,y = center(first_slot)
                pydirectinput.click(x,y)
                time.sleep(0.5)

            # Use potions by loops
            for potion,var in potion_vars.items():
                if var.get():
                    loops = int(potion_loops[p].get())
                    send_discord_message(f"Using {loops}x {potion}s!","using")
                    for _ in range(loops):
                        pydirectinput.click(x,y)
                        time.sleep(0.3)
                    send_discord_message(f"Successfully used {loops}x {potion}s","used")

            # Use Button
            use_btn = coords.get("Use Button")
            if use_btn:
                x,y = center(use_btn)
                pydirectinput.click(x,y)
                time.sleep(0.5)

            # Close Inventory
            close_inv = coords.get("Close Inventory")
            if close_inv:
                x,y = center(close_inv)
                pydirectinput.click(x,y)
                time.sleep(0.5)

        elif not detected:
            last_detected_biome = None
            # Middle screen click every 2s
            if mid and time.time()-last_middle_click>2:
                x,y = center(mid)
                pydirectinput.moveTo(x,y)
                pydirectinput.click(x,y)
                last_middle_click = time.time()
        if not running: return

start_btn.config(command=start_macro)
stop_btn.config(command=stop_macro)

def on_close():
    global running
    running=False
    root.destroy()

root.protocol("WM_DELETE_WINDOW",on_close)
root.mainloop()
