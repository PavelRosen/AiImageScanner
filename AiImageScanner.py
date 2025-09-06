import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, font
import os
import shutil
import base64
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import sv_ttk
import webbrowser

# --- Custom Exception for Quota Errors ---
class QuotaExceededError(Exception):
    pass

# --- START OF CORE LOGIC FUNCTIONS ---
def get_image_data(image_path):
    ext_to_mimetype = {'.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp', '.cr2':'image/x-canon-cr2', '.dng':'image/x-adobe-dng', '.tiff':'image/tiff'}
    file_ext = os.path.splitext(image_path.lower())[1]
    mime_type = ext_to_mimetype.get(file_ext)
    if not mime_type: return None, None
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    return base64_image, mime_type
def process_with_google(image_path, focus_keyword, api_key, debug_mode, log_callback):
    try:
        base64_image, mime_type = get_image_data(image_path)
        if not base64_image: return None
    except IOError as e:
        log_callback(f"Error reading file {os.path.basename(image_path)}: {e}")
        return None
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    prompt = f"You are an image analyst. Your task is to determine if '{focus_keyword}' is the main subject. Answer only 'yes' or 'no'."
    payload = {"contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": mime_type, "data": base64_image}}]}]}
    try:
        response = requests.post(api_url, json=payload, timeout=90)
        if response.status_code != 200:
            log_callback(f"Warning (Google): Bad status code {response.status_code} for {os.path.basename(image_path)}.")
            return None
        result = response.json()
        if "candidates" not in result or not result["candidates"]: return None
        text_result = result["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
        if 'yes' in text_result: return image_path
        return None
    except Exception as e:
        log_callback(f"Error (Google) with {os.path.basename(image_path)}: {e}")
        return None
def process_with_openai_compatible(image_path, focus_keyword, api_key, debug_mode, api_url, model_name, provider_name, log_callback):
    try:
        base64_image, mime_type = get_image_data(image_path)
        if not base64_image: return None
    except IOError as e:
        log_callback(f"Error reading file {os.path.basename(image_path)}: {e}")
        return None
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    prompt = f"You are an image analyst. Your task is to determine if '{focus_keyword}' is the main subject. Answer only 'yes' or 'no'."
    payload = { "model": model_name, "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}]}], "max_tokens": 10 }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        if response.status_code != 200:
            log_callback(f"Warning ({provider_name}): Bad status {response.status_code} for {os.path.basename(image_path)}.")
            return None
        result = response.json()
        text_result = result['choices'][0]['message']['content'].strip().lower()
        if 'yes' in text_result: return image_path
        return None
    except Exception as e:
        log_callback(f"Error ({provider_name}) with {os.path.basename(image_path)}: {e}")
        return None
def process_with_ollama(image_path, focus_keyword, model_name, mode, threshold, prompt_mode, temperature, log_callback):
    try:
        base64_image, _ = get_image_data(image_path)
        if not base64_image: return None
    except IOError as e:
        log_callback(f"Error reading file {os.path.basename(image_path)}: {e}")
        return None
    prompt = ""
    if mode == 'confidence':
        prompt = f"On a scale of 1 to 10, where 1 is 'not at all' and 10 is 'absolutely certain', how confident are you that the main subject of this image is a '{focus_keyword}'? Your response must be only the number."
    else: # mode == 'yesno'
        if prompt_mode == 'cot':
            prompt = f"First, briefly describe the image in one sentence. Then, based on your description, determine if a '{focus_keyword}' is the main subject. Finally, answer with a single word on a new line: 'yes' or 'no'."
        else: # Simple mode
            prompt = f"You are an expert image analyst. Your only task is to determine if the main subject of the image is a '{focus_keyword}'. Your entire response must be a single word: 'yes' or 'no'. Is the main subject a '{focus_keyword}'?"
    ollama_api_url = "http://localhost:11434/api/generate"
    payload = { "model": model_name, "prompt": prompt, "stream": False, "images": [base64_image], "options": { "temperature": temperature } }
    try:
        response = requests.post(ollama_api_url, json=payload, timeout=180)
        response.raise_for_status()
        response_text = json.loads(response.text)["response"].strip().lower()
        if mode == 'confidence':
            score = int(response_text.split('.')[0])
            if score >= threshold: return image_path
        else:
            final_answer = response_text.split('\n')[-1].strip()
            if 'yes' in final_answer: return image_path
        return None
    except requests.exceptions.RequestException:
        log_callback("Error: Could not connect to Ollama server. Is it running?")
        return "STOP"
    except Exception as e:
        log_callback(f"Error (Ollama) with {os.path.basename(image_path)}: {e}")
        return None

# ### <<< שינוי לפונקציה גמישה יותר
def process_output_files(image_list, target_folder, action, log_callback):
    if not image_list: return
    os.makedirs(target_folder, exist_ok=True)
    
    action_verb = "Copying" if action == 'copy' else "Moving"
    log_callback(f"\n{action_verb} {len(image_list)} images to folder: {target_folder} ...")
    
    for file_path in image_list:
        try:
            if action == 'copy':
                shutil.copy2(file_path, os.path.join(target_folder, os.path.basename(file_path)))
            elif action == 'move':
                shutil.move(file_path, os.path.join(target_folder, os.path.basename(file_path)))
        except Exception as e:
            log_callback(f"Error {action_verb.lower()} file {os.path.basename(file_path)}: {e}")
            
    log_callback(f"File {action} process is complete.")


def find_images_logic(params, progress_callback, log_callback, stop_event):
    directory = params['directory']
    focus_keyword = params['focus_keyword']
    provider = params['provider']
    recursive_scan = params.get('recursive', True)
    log_callback("Gathering image files...")
    supported_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.cr2', '.dng', '.tiff')
    image_list = []
    if recursive_scan:
        log_callback("Recursive scan enabled: Searching in subdirectories...")
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.lower().endswith(supported_extensions):
                    full_path = os.path.join(dirpath, filename)
                    image_list.append(full_path)
    else:
        log_callback("Recursive scan disabled: Searching in top-level directory only.")
        for filename in os.listdir(directory):
             if filename.lower().endswith(supported_extensions):
                full_path = os.path.join(directory, filename)
                if os.path.isfile(full_path): image_list.append(full_path)
    log_callback(f"Found {len(image_list)} images to analyze.")
    if not image_list:
        log_callback("Warning: No compatible images found.")
        return {}
    log_callback(f"Starting analysis using '{provider}' for '{focus_keyword}'...")
    found_images = {}
    args_list = []
    if provider == 'google':
        target_func = process_with_google
        args_list = [(img, focus_keyword, params['api_key'], params['debug_mode'], log_callback) for img in image_list]
    elif provider == 'chatgpt':
        def worker_chatgpt(image_path, focus_keyword, api_key, debug_mode):
            return process_with_openai_compatible(image_path, focus_keyword, api_key, debug_mode, api_url="https://api.openai.com/v1/chat/completions", model_name="gpt-4o", provider_name="ChatGPT", log_callback=log_callback)
        target_func = worker_chatgpt
        args_list = [(img, focus_keyword, params['api_key'], params['debug_mode']) for img in image_list]
    elif provider == 'deepseek':
        def worker_deepseek(image_path, focus_keyword, api_key, debug_mode):
             return process_with_openai_compatible(image_path, focus_keyword, api_key, debug_mode, api_url="https://api.deepseek.com/v1/chat/completions", model_name="deepseek-vl-chat", provider_name="DeepSeek", log_callback=log_callback)
        target_func = worker_deepseek
        args_list = [(img, focus_keyword, params['api_key'], params['debug_mode']) for img in image_list]
    elif provider == 'ollama':
        target_func = process_with_ollama
        args_list = [(img, focus_keyword, params['model_name'], params['mode'], params['threshold'], params['prompt_mode'], params['temperature'], log_callback) for img in image_list]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(target_func, *args): args[0] for args in args_list}
        processed_count = 0
        for future in as_completed(futures):
            if stop_event.is_set(): break
            result_path = future.result()
            if result_path == "STOP":
                log_callback("Stopping analysis due to connection error.")
                break
            if result_path: found_images[result_path] = [focus_keyword]
            processed_count += 1
            progress = (processed_count / len(image_list)) * 100
            progress_callback(progress)
    if stop_event.is_set():
        log_callback("\nScan stopped by user.")
    if found_images:
        log_callback(f"\n--- Found {len(found_images)} images where '{focus_keyword}' is the main subject ---")
        for path in found_images: log_callback(f"  - {os.path.basename(path)}")
    else:
        if not stop_event.is_set():
             log_callback(f"\nNo images were found where '{focus_keyword}' is the main subject.")
    
    destination_folder = params.get('destination_folder')
    action = params.get('action')
    if destination_folder and found_images:
        process_output_files(list(found_images.keys()), destination_folder, action, log_callback)
    
    log_callback("\nScan Finished.")
# --- END OF CORE LOGIC FUNCTIONS ---


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Image Scanner")
        self.geometry("850x700")

        sv_ttk.set_theme("dark")
        self.stop_event = threading.Event()

        # --- Variables ---
        self.dir_var = tk.StringVar()
        self.focus_var = tk.StringVar()
        self.destination_dir_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.action_var = tk.StringVar(value='copy') # ### <<< משתנה חדש לבחירה
        self.provider_var = tk.StringVar(value='ollama')
        self.api_key_var = tk.StringVar()
        self.debug_var = tk.BooleanVar(value=False)
        self.model_var = tk.StringVar(value='llava')
        self.mode_var = tk.StringVar(value='confidence')
        self.prompt_mode_var = tk.StringVar(value='simple')
        self.threshold_var = tk.IntVar(value=8)
        self.temp_var = tk.DoubleVar(value=0.1)

        self.api_key_var.set(os.getenv("GEMINI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "") or os.getenv("DEEPSEEK_API_KEY", ""))

        # --- Layout ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(3, weight=1) 
        main_frame.columnconfigure(0, weight=1)
        input_frame = ttk.LabelFrame(main_frame, text="Scan Settings", padding=15)
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        self.ollama_frame = ttk.LabelFrame(main_frame, text="Ollama Options", padding=15)
        self.ollama_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.ollama_frame.columnconfigure((1, 3), weight=1)
        output_frame = ttk.LabelFrame(main_frame, text="Output Log", padding=15)
        output_frame.grid(row=3, column=0, sticky="nsew", pady=10)
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)

        # --- Widgets for Input Frame ---
        ttk.Label(input_frame, text="Image Directory:").grid(row=0, column=0, sticky=tk.E, padx=10, pady=5)
        ttk.Entry(input_frame, textvariable=self.dir_var).grid(row=0, column=1, sticky=tk.EW, pady=5)
        ttk.Button(input_frame, text="Browse...", command=self.select_dir).grid(row=0, column=2, padx=10, pady=5)
        ttk.Checkbutton(input_frame, text="Scan subdirectories", variable=self.recursive_var).grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        ttk.Label(input_frame, text="Keyword:").grid(row=2, column=0, sticky=tk.E, padx=10, pady=5)
        ttk.Entry(input_frame, textvariable=self.focus_var).grid(row=2, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=5)
        
        # ### <<< שינוי טקסט וארגון מחדש
        ttk.Label(input_frame, text="Destination Folder (Optional):").grid(row=3, column=0, sticky=tk.E, padx=10, pady=5)
        ttk.Entry(input_frame, textvariable=self.destination_dir_var).grid(row=3, column=1, sticky=tk.EW, pady=5)
        ttk.Button(input_frame, text="Browse...", command=self.select_destination_dir).grid(row=3, column=2, padx=10, pady=5)
        
        action_frame = ttk.Frame(input_frame)
        action_frame.grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)
        ttk.Radiobutton(action_frame, text="Copy Files", variable=self.action_var, value="copy").pack(side=tk.LEFT, padx=(0,10))
        ttk.Radiobutton(action_frame, text="Move Files", variable=self.action_var, value="move").pack(side=tk.LEFT)
        
        ttk.Label(input_frame, text="Provider:").grid(row=5, column=0, sticky=tk.E, padx=10, pady=5)
        provider_frame = ttk.Frame(input_frame)
        provider_frame.grid(row=5, column=1, columnspan=2, sticky=tk.EW, pady=5)
        provider_menu = ttk.Combobox(provider_frame, textvariable=self.provider_var, values=['ollama', 'google', 'chatgpt', 'deepseek'], state="readonly")
        provider_menu.pack(side=tk.LEFT, padx=(10,0))
        provider_menu.bind("<<ComboboxSelected>>", self.toggle_ollama_options)
        instructions_button = ttk.Button(provider_frame, text="Local AI Instructions", command=self.show_local_ai_instructions)
        instructions_button.pack(side=tk.LEFT, padx=10)
        self.api_key_label = ttk.Label(input_frame, text="API Key:")
        self.api_key_label.grid(row=6, column=0, sticky=tk.E, padx=10, pady=5)
        self.api_key_entry = ttk.Entry(input_frame, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(row=6, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=5)
        ttk.Checkbutton(input_frame, text="Enable Debug Mode", variable=self.debug_var).grid(row=7, column=1, sticky=tk.W, padx=10, pady=5)

        # --- Widgets for Ollama Frame and others are unchanged ---
        ttk.Label(self.ollama_frame, text="Model:").grid(row=0, column=0, sticky=tk.E, padx=10, pady=5)
        ttk.Entry(self.ollama_frame, textvariable=self.model_var).grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)
        ttk.Label(self.ollama_frame, text="Temperature:").grid(row=0, column=2, sticky=tk.E, padx=10, pady=5)
        self.temp_spinbox = ttk.Spinbox(self.ollama_frame, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=10)
        self.temp_spinbox.grid(row=0, column=3, sticky=tk.W, padx=10, pady=5)
        ttk.Label(self.ollama_frame, text="Analysis Mode:").grid(row=1, column=0, sticky=tk.E, padx=10, pady=5)
        self.mode_menu = ttk.Combobox(self.ollama_frame, textvariable=self.mode_var, values=['confidence', 'yesno'], state="readonly")
        self.mode_menu.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)
        self.mode_menu.bind("<<ComboboxSelected>>", self.update_ollama_options_state)
        self.prompt_mode_label = ttk.Label(self.ollama_frame, text="Prompt Mode ('yesno'):")
        self.prompt_mode_label.grid(row=2, column=0, sticky=tk.E, padx=10, pady=5)
        self.prompt_mode_combo = ttk.Combobox(self.ollama_frame, textvariable=self.prompt_mode_var, values=['simple', 'cot'], state="readonly")
        self.prompt_mode_combo.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=5)
        self.threshold_label = ttk.Label(self.ollama_frame, text="Threshold ('confidence'):")
        self.threshold_label.grid(row=2, column=2, sticky=tk.E, padx=10, pady=5)
        self.threshold_spinbox = ttk.Spinbox(self.ollama_frame, from_=1, to=10, textvariable=self.threshold_var, width=10)
        self.threshold_spinbox.grid(row=2, column=3, sticky=tk.W, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state='disabled')
        self.log_text.grid(row=0, column=0, sticky="nsew")
        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(fill=tk.X, expand=True, pady=(0,5))
        action_frame.columnconfigure(0, weight=1)
        self.progress_bar = ttk.Progressbar(action_frame, orient='horizontal', mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        buttons_frame = ttk.Frame(action_frame)
        buttons_frame.grid(row=0, column=1, sticky="e")
        self.start_button = ttk.Button(buttons_frame, text="Start Scan", command=self.start_scan_thread)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = ttk.Button(buttons_frame, text="Stop", command=self.stop_scan, state="disabled")
        self.stop_button.pack(side=tk.LEFT)
        ttk.Separator(bottom_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        credits_frame = ttk.Frame(bottom_frame)
        credits_frame.pack(fill=tk.X, expand=True)
        donation_frame = ttk.Frame(credits_frame)
        donation_frame.pack(side=tk.RIGHT)
        about_and_credits_frame = ttk.Frame(credits_frame)
        about_and_credits_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        about_button = ttk.Button(about_and_credits_frame, text="About", command=self.show_about_window, width=8)
        about_button.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(about_and_credits_frame, text="Created By Pavel RST | Pavrst@proton.me").pack(side=tk.LEFT, padx=5)
        ttk.Label(donation_frame, text="Donate:").pack(side=tk.LEFT, padx=(10, 5))
        self.kofi_link = "https://ko-fi.com/pavelrst"
        link_font = font.Font(family="Segoe UI", size=9, underline=True)
        kofi_label = tk.Label(donation_frame, text=self.kofi_link, fg="#007bff", cursor="hand2", font=link_font)
        kofi_label.pack(side=tk.LEFT)
        kofi_label.bind("<Button-1>", self.open_link)
        ttk.Label(donation_frame, text=" | BTC:").pack(side=tk.LEFT, padx=(10, 5))
        self.btc_address = "BC1QM2E6SE7FUE4WEPMXU2ASM47AS59WVX4WL6WRXW"
        btc_entry = ttk.Entry(donation_frame, width=30)
        btc_entry.insert(0, self.btc_address)
        btc_entry.config(state="readonly")
        btc_entry.pack(side=tk.LEFT)
        self.copy_button = ttk.Button(donation_frame, text="Copy", command=self.copy_btc_address, width=5)
        self.copy_button.pack(side=tk.LEFT, padx=5)
        self.toggle_ollama_options()
        self.update_ollama_options_state()

    # --- METHODS ---
    def open_link(self, event):
        webbrowser.open_new(self.kofi_link)
    def copy_btc_address(self):
        self.clipboard_clear()
        self.clipboard_append(self.btc_address)
        self.log_message("BTC address copied to clipboard!")
        original_text = self.copy_button.cget("text")
        self.copy_button.config(text="Copied!")
        self.after(2000, lambda: self.copy_button.config(text=original_text))
    def show_about_window(self):
        about_win = tk.Toplevel(self)
        about_win.title("About AI Image Scanner")
        about_win.geometry("650x500")
        about_win.transient(self)
        about_win.grab_set()
        frame = ttk.Frame(about_win, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state='normal', relief=tk.FLAT, padx=5)
        text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        about_text = """
About AI Image Scanner
--------------------------------------------------------------------------------
This tool is designed to automate the tedious process of sorting through large photo collections to find specific subjects. It leverages the power of modern multimodal AI models to "look" at each image and determine if it matches a keyword you provide.
How It Works
--------------------------------------------------------------------------------
1.  You select a directory containing your images and provide a keyword (e.g., "bird", "car", "sunset").
2.  The tool scans the directory (and its subdirectories, if enabled) for all supported image files.
3.  For each image, it sends the image data to a selected AI model with a simple question: "Does this image prominently feature a 'keyword'?".
4.  If the AI model confidently answers "yes", the image is marked as a match.
5.  After the scan, all matched images are listed, and you have the option to automatically copy them to a new, organized folder.
Key Features
--------------------------------------------------------------------------------
- Multiple AI Providers: Choose between using a completely private and free local AI model via Ollama, or powerful cloud-based models from Google, OpenAI (ChatGPT), and DeepSeek for maximum accuracy.
- Advanced Local AI Control: When using Ollama, you can fine-tune the AI's behavior, including its "creativity" (temperature) and the confidence threshold required for a match.
- Recursive Scanning: Can search through complex folder structures, not just a single directory.
- Broad Format Support: Analyzes standard formats like JPG and PNG, as well as professional formats like TIFF, CR2, and DNG.
- User-Friendly Interface: All the power of this technology is accessible through a simple graphical interface, with no command-line knowledge required.
"""
        header_font = font.Font(family="Segoe UI", size=12, weight="bold")
        text_area.tag_configure("header", font=header_font, spacing1=5, spacing3=10)
        lines = about_text.strip().split('\n')
        for line in lines:
            if line.startswith('About AI Image Scanner') or line.startswith('How It Works') or line.startswith('Key Features'):
                text_area.insert(tk.END, line + '\n', "header")
            else:
                text_area.insert(tk.END, line + '\n')
        text_area.config(state='disabled')
        close_button = ttk.Button(frame, text="Close", command=about_win.destroy)
        close_button.pack(pady=10)
    def show_local_ai_instructions(self):
        instructions_win = tk.Toplevel(self)
        instructions_win.title("Local AI (Ollama) Setup Instructions")
        instructions_win.geometry("800x650")
        instructions_win.transient(self)
        instructions_win.grab_set()
        frame = ttk.Frame(instructions_win, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state='normal', relief=tk.FLAT, padx=5)
        text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        instructions_text = """
Local AI (Ollama) Setup Guide
This guide will help you set up a local, private, and free AI model on your computer to use with this tool.
--------------------------------------------------------------------------------
Step 1: Download and Install Ollama
--------------------------------------------------------------------------------
1. Go to the official Ollama website: https://ollama.com
2. Download the installer for your operating system (Windows, macOS, or Linux).
3. Run the installer and follow the on-screen instructions.
After installation, Ollama will run in the background.
--------------------------------------------------------------------------------
Step 2: Download a Vision Model
--------------------------------------------------------------------------------
You need a multimodal (vision) model to analyze images. LLaVA is a great choice.
1. Open a Terminal (on macOS/Linux) or Command Prompt (on Windows).
2. Type the following command and press Enter:
   ollama run llava
3. This will start a large download. Once finished, you can close the terminal.
You can also download other compatible vision models, for example:
   ollama run bakllava
   ollama run moondream
--------------------------------------------------------------------------------
Step 3: You're Ready!
--------------------------------------------------------------------------------
As long as the Ollama application is running, this scanner can use it.
- Select "ollama" as the provider in the main window.
- Enter the model name you downloaded (e.g., "llava") in the Model field.
- You do not need an API Key for Ollama.
--------------------------------------------------------------------------------
Step 4: Understanding the Ollama Options
--------------------------------------------------------------------------------
These settings give you fine-grained control over the AI's behavior.
Model:
The name of the model you downloaded with the `ollama run` command. You can have multiple models installed and switch between them here.
Temperature:
Think of this as a "creativity knob".
- Low value (e.g., 0.1): The AI will be very strict, factual, and repetitive. Perfect for "yes/no" questions.
- High value (e.g., 0.8): The AI will be more creative and "talkative".
For this tool, it's best to keep the temperature low (0.1 - 0.2) for accurate results.
Analysis Mode:
This changes the fundamental question asked to the AI.
- confidence: Asks the AI "How sure are you (1-10)?". This gives you more control to filter out uncertain results.
- yesno: Asks the AI "Is it there, yes or no?". This is faster and more direct.
Threshold (for 'confidence' mode):
The minimum confidence score (from 1 to 10) for an image to be considered a match. A threshold of 8 means you only want images the model is very sure about.
Prompt Mode (for 'yesno' mode):
Changes the strategy used to ask the "yes/no" question.
- simple: A direct, straightforward question. Faster and usually good enough.
- cot (Chain of Thought): Tells the model to "think step-by-step" before answering. This can sometimes be more accurate but is slightly slower.
"""
        bold_font = font.Font(family="Segoe UI", size=10, weight="bold")
        header_font = font.Font(family="Segoe UI", size=12, weight="bold")
        text_area.tag_configure("bold", font=bold_font)
        text_area.tag_configure("header", font=header_font, spacing1=5, spacing3=10)
        text_area.tag_configure("link", foreground="#007bff", underline=True)
        text_area.tag_configure("option_header", font=bold_font, spacing1=8, spacing3=2)
        lines = instructions_text.strip().split('\n')
        for line in lines:
            if line.startswith('Step'):
                text_area.insert(tk.END, line + '\n', "header")
            elif line.startswith('   ollama run'):
                text_area.insert(tk.END, line + '\n', "bold")
            elif 'https://ollama.com' in line:
                start_index = text_area.index(tk.END + f"-{len(line)+1}c")
                text_area.insert(tk.END, line + '\n')
                end_index = text_area.index(tk.END + "-1c")
                text_area.tag_add("link", start_index, end_index)
            elif line.strip().endswith(':'):
                text_area.insert(tk.END, line + '\n', "option_header")
            else:
                text_area.insert(tk.END, line + '\n')
        text_area.config(state='disabled')
        close_button = ttk.Button(frame, text="Close", command=instructions_win.destroy)
        close_button.pack(pady=10)
    def select_dir(self):
        path = filedialog.askdirectory(title="Select Image Directory")
        if path: self.dir_var.set(path)
    def select_destination_dir(self):
        path = filedialog.askdirectory(title="Select Destination Directory")
        if path: self.destination_dir_var.set(path)
    def toggle_ollama_options(self, event=None):
        is_ollama = self.provider_var.get() == 'ollama'
        state = 'normal' if is_ollama else 'disabled'
        for widget in self.ollama_frame.winfo_children():
            widget.configure(state=state)
        api_state = 'disabled' if is_ollama else 'normal'
        self.api_key_label.config(state=api_state)
        self.api_key_entry.config(state=api_state)
        self.update_ollama_options_state()
    def update_ollama_options_state(self, event=None):
        if self.provider_var.get() != 'ollama':
            is_yesno = False
        else:
            is_yesno = self.mode_var.get() == 'yesno'
        self.prompt_mode_label.config(state='normal' if is_yesno else 'disabled')
        prompt_combo_state = 'readonly' if is_yesno and self.provider_var.get() == 'ollama' else 'disabled'
        self.prompt_mode_combo.config(state=prompt_combo_state)
        self.threshold_label.config(state='disabled' if is_yesno else 'normal')
        threshold_spin_state = 'normal' if not is_yesno and self.provider_var.get() == 'ollama' else 'disabled'
        self.threshold_spinbox.config(state=threshold_spin_state)
    def log_message(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
    def update_progress(self, value):
        self.progress_bar['value'] = value
    def stop_scan(self):
        self.log_message("Stop signal received. Finishing current image analysis...")
        self.stop_event.set()
        self.stop_button.config(state="disabled")
    def start_scan_thread(self):
        params = {
            'directory': self.dir_var.get(), 'focus_keyword': self.focus_var.get(),
            'destination_folder': self.destination_dir_var.get() or None,
            'action': self.action_var.get(),
            'recursive': self.recursive_var.get(),
            'provider': self.provider_var.get(),
            'api_key': self.api_key_var.get(), 'debug_mode': self.debug_var.get(),
            'model_name': self.model_var.get(), 'mode': self.mode_var.get(),
            'prompt_mode': self.prompt_mode_var.get(), 'threshold': self.threshold_var.get(),
            'temperature': self.temp_var.get(),
        }
        if not params['directory'] or not params['focus_keyword']:
            self.log_message("Error: Please provide an image directory and a keyword.")
            return
        if params['provider'] != 'ollama' and not params['api_key']:
             self.log_message(f"Error: API Key is required for provider '{params['provider']}'.")
             return
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.stop_event.clear()
        self.progress_bar['value'] = 0
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')
        scan_thread = threading.Thread(target=self.run_scan_logic, args=(params,), daemon=True)
        scan_thread.start()
    def run_scan_logic(self, params):
        try:
            find_images_logic(params, self.update_progress, self.log_message, self.stop_event)
        except Exception as e:
            self.log_message(f"A critical error occurred: {e}")
        finally:
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')

if __name__ == "__main__":
    app = App()
    app.mainloop()