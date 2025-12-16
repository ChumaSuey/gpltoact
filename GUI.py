import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import struct
import re
from struct import pack

# ==========================================
# FIX: TCL/TK Library Discovery
# ==========================================
# Fix for TCL/TK Library not being found on windows, had to apply it in several scripts now
# - Chuma

def fix_tcl_env():
    """
    Robustly fixes the TCL/TK environment variables for Windows users.
    Searches for init.tcl and sets TCL_LIBRARY and TK_LIBRARY accordingly.
    """
    if sys.platform != 'win32':
        return

    try:
        base_paths = [
            os.path.dirname(sys.executable),  # e.g. .venv/Scripts
            os.path.dirname(os.path.dirname(sys.executable)), # e.g. .venv
            # Add Python install root if we are in a venv
            os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))) if 'venv' in sys.executable.lower() else None,
            # Fallback to AppData/Local/Programs/Python/Python313 if clearly visible in error
            r"C:\Users\luism\AppData\Local\Programs\Python\Python313",
        ]
        
        # Filter None
        base_paths = [p for p in base_paths if p and os.path.exists(p)]

        tcl_library = None
        tk_library = None

        # Helper to check if a path looks like a valid tcl library (contains init.tcl)
        def is_valid_tcl_lib(path):
            return os.path.exists(os.path.join(path, "init.tcl"))

        for base in base_paths:
            # Look in tcl/tcl8.6, tcl8.6, lib/tcl8.6, etc.
            # Common locations:
            # - Python/tcl/tcl8.6
            # - Python/Lib/tcl8.6
            # - Python/share/tcl8.6
            
            candidates = [
                os.path.join(base, "tcl", "tcl8.6"),
                os.path.join(base, "tcl", "tcl8.7"), # Future proofing
                os.path.join(base, "lib", "tcl8.6"), # Python standard
                os.path.join(base, "tcl8.6"),         # Sometimes at root
            ]
            
            # Use os.walk for a deeper search if needed, but sticking to candidates first for speed
            for cand in candidates:
                if is_valid_tcl_lib(cand):
                    tcl_library = cand
                    # TK usually is sibling
                    parent = os.path.dirname(cand)
                    tk_candidates = [
                         os.path.join(parent, "tk8.6"),
                         os.path.join(parent, "tk8.7"),
                    ]
                    for tk_cand in tk_candidates:
                        if os.path.exists(tk_cand):
                            tk_library = tk_cand
                            break
                    break
            
            if tcl_library:
                break
        
        # Super-force fallback if still finding nothing but we know the path from the error log
        if not tcl_library:
             # Try specifically the Python 3.13 tcl path seen in error
             fallback_tcl = r"C:\Users\luism\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
             if is_valid_tcl_lib(fallback_tcl):
                 tcl_library = fallback_tcl
                 tk_library = r"C:\Users\luism\AppData\Local\Programs\Python\Python313\tcl\tk8.6"

        if tcl_library:
            print(f"DEBUG: Found TCL_LIBRARY at {tcl_library}")
            os.environ['TCL_LIBRARY'] = tcl_library
            # If TK not found, usually it's safely assumed to be near TCL, but let's be safe
            if tk_library:
                 print(f"DEBUG: Found TK_LIBRARY at {tk_library}")
                 os.environ['TK_LIBRARY'] = tk_library
        else:
            print("WARNING: Could not automatically find TCL/TK libraries.")

    except Exception as e:
        print(f"Warning: Error during TCL fix: {e}")

fix_tcl_env()

# ==========================================
# CORE FUNCTIONS
# ==========================================

def parse_adobe_act(filename):
    filesize = os.path.getsize(filename)
    with open(filename, 'rb') as file:
        if filesize == 772:  # CS2
            file.seek(768, 0)
            nbcolors = struct.unpack('>H', file.read(2))[0]
            file.seek(0, 0)
        else:
            nbcolors = filesize // 3
        return [struct.unpack('3B', file.read(3)) for i in range(nbcolors)]

def return_gimp_palette(colors, name, columns=0):
    return 'GIMP Palette\nName: {name}\nColumns: {columns}\n#\n{colors}\n'.format(
        name=name,
        columns=columns,
        colors='\n'.join(
            '{0} {1} {2}\tUntitled'.format(*color) for color in colors
        ),
    )

def parse_gpl_file(filename):
    colors = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = re.split(r'\s+', line.strip())
            try:
                nums = [int(x) for x in parts if x.isdigit()][:3]
                if len(nums) >= 3:
                    r, g, b = [max(0, min(255, x)) for x in nums[:3]]
                    colors.append((r, g, b))
            except (ValueError, IndexError):
                continue
    return colors

def create_act_file(colors, output_filename):
    with open(output_filename, 'wb') as f:
        for r, g, b in colors[:256]:
            f.write(pack('3B', r, g, b))
        for _ in range(256 - len(colors)):
            f.write(pack('3B', 0, 0, 0))
        if len(colors) > 0 and len(colors) < 256:
            f.write(pack('>H', len(colors)))

# ==========================================
# GUI APP
# ==========================================

class PaletteConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Palette Converter")
        self.geometry("600x450")
        
        # Theme Colors
        self.colors = {
            "bg": "#16213e",       # Deep Void
            "fg": "#ffffff",       # Starlight
            "accent": "#A42F43",   # Designer Red
            "secondary": "#0f3460",# Twilight Blue
            "input_bg": "#1a1a2e", # Darker Void
            "success": "#4cc9f0",   # Light Blue
            "disabled": "#535c68",  # Greyed out
            "browse_bg": "#3498db", # Calmer Blue for Browse
            "browse_fg": "#ffffff"  # White text for better contrast
        }
        
        self.configure(bg=self.colors["bg"])
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self._configure_styles()
        
        self._create_widgets()

    def _configure_styles(self):
        # Configure Frames
        self.style.configure(
            "TFrame", 
            background=self.colors["bg"]
        )
        self.style.configure(
            "TLabel", 
            background=self.colors["bg"], 
            foreground=self.colors["fg"],
            font=("Segoe UI", 10)
        )
        
        # Configure Notebook (Tabs)
        self.style.configure(
            "TNotebook", 
            background=self.colors["bg"], 
            borderwidth=0
        )
        self.style.configure(
            "TNotebook.Tab", 
            background=self.colors["secondary"], 
            foreground=self.colors["fg"],
            padding=[15, 5],
            font=("Segoe UI", 10, "bold")
        )
        self.style.map(
            "TNotebook.Tab", 
            background=[("selected", self.colors["accent"])],
            foreground=[("selected", "#ffffff")]
        )
        
        # Configure Buttons
        self.style.configure(
            "Accent.TButton",
            background=self.colors["accent"],
            foreground="#ffffff",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padding=10
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", "#c23b53"), ("pressed", "#822536"), ("disabled", self.colors["disabled"])]
        )

        # distinct Browse Button
        self.style.configure(
            "Browse.TButton",
            background=self.colors["browse_bg"],
            foreground=self.colors["browse_fg"],
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
            padding=5
        )
        self.style.map(
            "Browse.TButton",
            background=[("active", "#5dade2"), ("pressed", "#2980b9")]
        )

        self.style.configure(
            "Secondary.TButton",
            background=self.colors["secondary"],
            foreground=self.colors["fg"],
            borderwidth=0,
            font=("Segoe UI", 9)
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", "#16213e")]
        )

    def _create_widgets(self):
        # Header
        header_frame = tk.Frame(self, bg=self.colors["bg"])
        header_frame.pack(fill="x", padx=20, pady=20)
        
        title = tk.Label(
            header_frame, 
            text="Palette Converter", 
            font=("Segoe UI", 24, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["accent"]
        )
        title.pack(side="left")

        subtitle = tk.Label(
            header_frame,
            text="By Chuma",
            font=("Segoe UI", 12, "italic"),
            bg=self.colors["bg"],
            fg=self.colors["fg"]
        )
        subtitle.pack(side="left", padx=(10, 0), pady=(10, 0))

        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Tab 1: ACT to GPL
        self.tab_act_to_gpl = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_act_to_gpl, text=" ACT  ➜  GPL ")
        self._build_act_to_gpl_tab()
        
        # Tab 2: GPL to ACT
        self.tab_gpl_to_act = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_gpl_to_act, text=" GPL  ➜  ACT ")
        self._build_gpl_to_act_tab()

    def _build_act_to_gpl_tab(self):
        container = tk.Frame(self.tab_act_to_gpl, bg=self.colors["bg"])
        container.pack(fill="both", expand=True, padx=40, pady=40)
        
        # File Selection
        lbl = ttk.Label(container, text="Select Adobe Palette (.act):")
        lbl.pack(anchor="w", pady=(0, 5))
        
        file_frame = tk.Frame(container, bg=self.colors["bg"])
        file_frame.pack(fill="x", pady=(0, 20))
        
        self.act_path_var = tk.StringVar()
        self.act_path_var.trace("w", self._validate_act_input) # Monitor changes

        entry = tk.Entry(
            file_frame, 
            textvariable=self.act_path_var,
            bg=self.colors["input_bg"],
            fg=self.colors["fg"],
            insertbackground="white",
            bd=0,
            relief="flat",
            font=("Consolas", 10)
        )
        entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        
        btn_browse = ttk.Button(
            file_frame, 
            text="BROWSE...", 
            style="Browse.TButton",
            command=lambda: self._browse_file(self.act_path_var, "act")
        )
        btn_browse.pack(side="right")
        
        # Convert Button
        self.btn_convert_act = ttk.Button(
            container, 
            text="CONVERT TO .GPL (GIMP)", 
            style="Accent.TButton",
            command=self._convert_act_to_gpl,
            state="disabled" # Default to disabled
        )
        self.btn_convert_act.pack(fill="x", pady=20)

    def _build_gpl_to_act_tab(self):
        container = tk.Frame(self.tab_gpl_to_act, bg=self.colors["bg"])
        container.pack(fill="both", expand=True, padx=40, pady=40)
        
        # File Selection
        lbl = ttk.Label(container, text="Select GIMP Palette (.gpl):")
        lbl.pack(anchor="w", pady=(0, 5))
        
        file_frame = tk.Frame(container, bg=self.colors["bg"])
        file_frame.pack(fill="x", pady=(0, 20))
        
        self.gpl_path_var = tk.StringVar()
        self.gpl_path_var.trace("w", self._validate_gpl_input) # Monitor changes

        entry = tk.Entry(
            file_frame, 
            textvariable=self.gpl_path_var,
            bg=self.colors["input_bg"],
            fg=self.colors["fg"],
            insertbackground="white",
            bd=0,
            relief="flat",
            font=("Consolas", 10)
        )
        entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        
        btn_browse = ttk.Button(
            file_frame, 
            text="BROWSE...", 
            style="Browse.TButton",
            command=lambda: self._browse_file(self.gpl_path_var, "gpl")
        )
        btn_browse.pack(side="right")
        
        # Convert Button
        self.btn_convert_gpl = ttk.Button(
            container, 
            text="CONVERT TO .ACT (ADOBE)", 
            style="Accent.TButton",
            command=self._convert_gpl_to_act,
            state="disabled" # Default to disabled
        )
        self.btn_convert_gpl.pack(fill="x", pady=20)

    def _validate_act_input(self, *args):
        if self.act_path_var.get().strip():
            self.btn_convert_act.configure(state="normal")
        else:
            self.btn_convert_act.configure(state="disabled")

    def _validate_gpl_input(self, *args):
        if self.gpl_path_var.get().strip():
            self.btn_convert_gpl.configure(state="normal")
        else:
            self.btn_convert_gpl.configure(state="disabled")

    def _browse_file(self, var, ftype):
        if ftype == "act":
            path = filedialog.askopenfilename(filetypes=[("Adobe Palette", "*.act"), ("All Files", "*.*")])
        else:
            path = filedialog.askopenfilename(filetypes=[("GIMP Palette", "*.gpl"), ("All Files", "*.*")])
        
        if path:
            var.set(path)

    def _convert_act_to_gpl(self):
        input_path = self.act_path_var.get()
        if not input_path:
            # Should not happen if button disabled, but safe check
            return

        try:
            colors = parse_adobe_act(input_path)
            
            output_path = filedialog.asksaveasfilename(
                defaultextension=".gpl",
                initialfile=os.path.splitext(os.path.basename(input_path))[0] + ".gpl",
                filetypes=[("GIMP Palette", "*.gpl")]
            )
            
            if output_path:
                with open(output_path, 'w') as f:
                    f.write(return_gimp_palette(colors, os.path.basename(output_path)))
                messagebox.showinfo("Success", f"Converted successfully!\nSaved to: {output_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert:\n{str(e)}")

    def _convert_gpl_to_act(self):
        input_path = self.gpl_path_var.get()
        if not input_path:
            return

        try:
            colors = parse_gpl_file(input_path)
            if not colors:
                messagebox.showerror("Error", "No valid colors found in the GPL file.")
                return

            output_path = filedialog.asksaveasfilename(
                defaultextension=".act",
                initialfile=os.path.splitext(os.path.basename(input_path))[0] + ".act",
                filetypes=[("Adobe Palette", "*.act")]
            )
            
            if output_path:
                create_act_file(colors, output_path)
                messagebox.showinfo("Success", f"Converted successfully!\nSaved to: {output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert:\n{str(e)}")


if __name__ == "__main__":
    app = PaletteConverterApp()
    app.mainloop()
