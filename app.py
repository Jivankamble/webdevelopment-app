# coding: utf-8
import sys
import os
import re
import time
import json
import queue
import threading
import multiprocessing
import customtkinter as ctk
from tkinter import filedialog, messagebox, font
from PyQt6 import QtWidgets, QtWebEngineWidgets, QtCore
import requests
import tkinter as tk
# ====================== Preview Process ======================
class PreviewProcess(multiprocessing.Process):
    def __init__(self, comm_queue):
        super().__init__()
        self.comm_queue = comm_queue
        self.daemon = True

    def run(self):
        class PreviewWindow(QtWidgets.QMainWindow):
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
                self.browser = QtWebEngineWidgets.QWebEngineView()
                self.setCentralWidget(self.browser)
                self.resize(1280, 720)
                self.setWindowTitle("Live Preview")
                self.timer = QtCore.QTimer()
                self.timer.timeout.connect(self.check_queue)
                self.timer.start(100)

            def check_queue(self):
                try:
                    if not self.queue.empty():
                        html = self.queue.get_nowait()
                        self.browser.setHtml(html)
                except:
                    pass

        app = QtWidgets.QApplication(sys.argv)
        window = PreviewWindow(self.comm_queue)
        window.show()
        app.exec()

# ====================== Main Application ======================
class CodeBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CodeBot - AI Web Studio")
        self.geometry("1400x900")
        self.api_key = "AIzaSyDVKIgfwT_1S-lzuS3mRW-ZPkgrxJT0pVY"  # Replace with your key
        
        # VS Code color scheme
        self.vs_code_theme = {
            'background': '#1E1E1E',
            'foreground': '#D4D4D4',
            'html': {
                'tag': '#569CD6',
                'attr': '#9CDCFE',
                'string': '#CE9178'
            },
            'css': {
                'selector': '#D7BA7D',
                'property': '#9CDCFE',
                'value': '#CE9178'
            },
            'js': {
                'keyword': '#569CD6',
                'function': '#DCDCAA',
                'string': '#CE9178',
                'number': '#B5CEA8'
            }
        }
        
        # Communication with preview process
        self.preview_queue = multiprocessing.Queue()
        self.preview_process = None
        
        # UI Setup
        self.setup_ui()
        self.setup_syntax_highlighting()
        self.setup_event_handlers()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Editor Panel
        editor_frame = ctk.CTkFrame(self)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Code Tabs
        self.tabs = ctk.CTkTabview(editor_frame)
        self.tabs.pack(fill="both", expand=True)

        self.html_editor = self.create_editor_tab("HTML")
        self.css_editor = self.create_editor_tab("CSS")
        self.js_editor = self.create_editor_tab("JavaScript")

        # Control Panel
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        self.prompt_entry = ctk.CTkEntry(
            control_frame,
            placeholder_text="Describe your website...",
            font=("Roboto", 14)
        )
        self.prompt_entry.pack(side="left", padx=5, fill="x", expand=True)

        ctk.CTkButton(
            control_frame,
            text="Generate",
            command=self.start_generation,
            fg_color="#2ECC71",
            hover_color="#27AE60",
            width=120
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            control_frame,
            text="Live Preview",
            command=self.toggle_preview,
            fg_color="#3498DB",
            hover_color="#2980B9",
            width=120
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            control_frame,
            text="Save Project",
            command=self.save_project,
            fg_color="#7F8C8D",
            hover_color="#95A5A6",
            width=120
        ).pack(side="right", padx=5)

    def create_editor_tab(self, title):
        tab = self.tabs.add(title)
        frame = ctk.CTkFrame(tab)
        frame.pack(fill="both", expand=True)
        
        # Use Tkinter Text widget for better syntax highlighting control
        editor = tk.Text(
            frame,
            wrap="none",
            font=("Consolas", 14),
            bg=self.vs_code_theme['background'],
            fg=self.vs_code_theme['foreground'],
            insertbackground=self.vs_code_theme['foreground'],
            selectbackground='#264F78',
            relief="flat"
        )
        editor.pack(fill="both", expand=True, padx=2, pady=2)
        return editor

    def setup_syntax_highlighting(self):
        # Configure tags for HTML
        self.html_editor.tag_configure('tag', foreground=self.vs_code_theme['html']['tag'])
        self.html_editor.tag_configure('attr', foreground=self.vs_code_theme['html']['attr'])
        self.html_editor.tag_configure('string', foreground=self.vs_code_theme['html']['string'])

        # Configure tags for CSS
        self.css_editor.tag_configure('selector', foreground=self.vs_code_theme['css']['selector'])
        self.css_editor.tag_configure('property', foreground=self.vs_code_theme['css']['property'])
        self.css_editor.tag_configure('value', foreground=self.vs_code_theme['css']['value'])

        # Configure tags for JavaScript
        self.js_editor.tag_configure('keyword', foreground=self.vs_code_theme['js']['keyword'])
        self.js_editor.tag_configure('function', foreground=self.vs_code_theme['js']['function'])
        self.js_editor.tag_configure('string', foreground=self.vs_code_theme['js']['string'])
        self.js_editor.tag_configure('number', foreground=self.vs_code_theme['js']['number'])

        threading.Thread(target=self.highlight_worker, daemon=True).start()

    def highlight_worker(self):
        while True:
            self.highlight_editor(self.html_editor, 'html')
            self.highlight_editor(self.css_editor, 'css')
            self.highlight_editor(self.js_editor, 'js')
            time.sleep(0.3)

    def highlight_editor(self, editor, lang):
        content = editor.get("1.0", "end-1c")
        editor.tag_remove("highlight", "1.0", "end")
        
        if lang == 'html':
            self.apply_regex(editor, r'<\/?[\w]+', 'tag')
            self.apply_regex(editor, r'\b[\w-]+(?=\=)', 'attr')
            self.apply_regex(editor, r'["\'].*?["\']', 'string')
        elif lang == 'css':
            self.apply_regex(editor, r'[\w-]+\s*(?={)', 'selector')
            self.apply_regex(editor, r'[\w-]+(?=\:)', 'property')
            self.apply_regex(editor, r':\s*.*?;', 'value')
        elif lang == 'js':
            keywords = ['function', 'const', 'let', 'if', 'else', 'return', 'class', 'export', 'import']
            self.apply_regex(editor, r'\b('+'|'.join(keywords)+r')\b', 'keyword')
            self.apply_regex(editor, r'\b\d+\b', 'number')
            self.apply_regex(editor, r'["\'].*?["\']', 'string')
            self.apply_regex(editor, r'function\s+([\w]+)', 'function')

    def apply_regex(self, editor, pattern, tag):
        for match in re.finditer(pattern, editor.get("1.0", "end-1c")):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            editor.tag_add(tag, start, end)

    def setup_event_handlers(self):
        for editor in [self.html_editor, self.css_editor, self.js_editor]:
            editor.bind("<KeyRelease>", lambda e: self.update_preview())

    def toggle_preview(self):
        if not self.preview_process or not self.preview_process.is_alive():
            self.preview_process = PreviewProcess(self.preview_queue)
            self.preview_process.start()
            time.sleep(1)  # Allow window initialization
        self.update_preview()

    def update_preview(self):
        html_content = f"""<!DOCTYPE html>
        <html>
            <head><style>{self.css_editor.get("1.0", "end")}</style></head>
            <body>{self.html_editor.get("1.0", "end")}</body>
            <script>{self.js_editor.get("1.0", "end")}</script>
        </html>"""
        self.preview_queue.put(html_content)

    def start_generation(self):
        prompt = self.prompt_entry.get()
        if not prompt:
            return
            
        threading.Thread(target=self.generate_code, args=(prompt,)).start()

    def generate_code(self, prompt):
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
                json={"contents": [{"parts": [{"text": f"{prompt}\n\nProvide separate HTML, CSS, and JavaScript code blocks."}]}]}
            )
            response.raise_for_status()
            
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            html = self.extract_code(content, "html")
            css = self.extract_code(content, "css")
            js = self.extract_code(content, "javascript")
            
            self.html_editor.delete("1.0", "end")
            self.html_editor.insert("end", html)
            self.css_editor.delete("1.0", "end")
            self.css_editor.insert("end", css)
            self.js_editor.delete("1.0", "end")
            self.js_editor.insert("end", js)
            
            messagebox.showinfo("Success", "Code generated successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def extract_code(self, text, lang):
        match = re.search(rf"```{lang}.*?\n(.*?)```", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def save_project(self):
        try:
            directory = filedialog.askdirectory()
            if directory:
                self.save_file(os.path.join(directory, "index.html"), self.html_editor.get("1.0", "end"))
                self.save_file(os.path.join(directory, "style.css"), self.css_editor.get("1.0", "end"))
                self.save_file(os.path.join(directory, "script.js"), self.js_editor.get("1.0", "end"))
                messagebox.showinfo("Success", "Project saved successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_file(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())

    def on_closing(self):
        if self.preview_process and self.preview_process.is_alive():
            self.preview_process.terminate()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("dark-blue")
    app = CodeBot()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()