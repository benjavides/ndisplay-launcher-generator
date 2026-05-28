from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ndisplay_launcher_generator.launcher_writer import (
    LaunchProfile,
    create_windows_shortcut,
    write_launch_profile,
)
from ndisplay_launcher_generator.map_discovery import discover_project_maps
from ndisplay_launcher_generator.unreal_detect import detect_unreal_installs


class GeneratorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("nDisplay Launcher Generator")
        self.root.geometry("920x380")
        self.root.minsize(860, 340)
        self.root.resizable(True, False)

        self.engine_var = tk.StringVar()
        self.uproject_var = tk.StringVar()
        self.ndisplay_var = tk.StringVar()
        self.map_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.launcher_name_var = tk.StringVar(value="Launch_nDisplay")
        self.icon_var = tk.StringVar()
        self.node_name_var = tk.StringVar(value="Node_0")
        self.stage_name_var = tk.StringVar(value="Node_0")
        self.status_var = tk.StringVar(value="Select paths and generate a launcher.")

        self.map_values: list[str] = []
        self.detected_engine_paths: list[str] = []

        self._build_ui()
        self._load_unreal_installations()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.LabelFrame(frame, text="Launcher Settings", padding=10)
        input_frame.grid(row=0, column=0, sticky=tk.EW)

        ttk.Label(input_frame, text="Unreal Editor").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.engine_combo = ttk.Combobox(input_frame, textvariable=self.engine_var, state="normal")
        self.engine_combo.grid(row=0, column=1, sticky=tk.EW, padx=6, pady=3)
        ttk.Button(input_frame, text="Browse...", command=self._pick_unreal_editor).grid(row=0, column=2, pady=3)

        ttk.Label(input_frame, text=".uproject").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(input_frame, textvariable=self.uproject_var).grid(row=1, column=1, sticky=tk.EW, padx=6, pady=3)
        ttk.Button(input_frame, text="Browse...", command=self._pick_uproject).grid(row=1, column=2, pady=3)

        ttk.Label(input_frame, text=".ndisplay").grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Entry(input_frame, textvariable=self.ndisplay_var).grid(row=2, column=1, sticky=tk.EW, padx=6, pady=3)
        ttk.Button(input_frame, text="Browse...", command=self._pick_ndisplay).grid(row=2, column=2, pady=3)

        ttk.Label(input_frame, text="Map").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.map_combo = ttk.Combobox(input_frame, textvariable=self.map_var, state="readonly")
        self.map_combo.grid(row=3, column=1, sticky=tk.EW, padx=6, pady=3)
        ttk.Button(input_frame, text="Refresh maps", command=self._refresh_maps).grid(row=3, column=2, pady=3)

        ttk.Label(input_frame, text="Output folder").grid(row=4, column=0, sticky=tk.W, pady=3)
        ttk.Entry(input_frame, textvariable=self.output_dir_var).grid(row=4, column=1, sticky=tk.EW, padx=6, pady=3)
        ttk.Button(input_frame, text="Browse...", command=self._pick_output_dir).grid(row=4, column=2, pady=3)

        ttk.Label(input_frame, text="Launcher name").grid(row=5, column=0, sticky=tk.W, pady=3)
        ttk.Entry(input_frame, textvariable=self.launcher_name_var).grid(row=5, column=1, sticky=tk.EW, padx=6, pady=3)

        ttk.Label(input_frame, text="Shortcut icon (optional)").grid(row=6, column=0, sticky=tk.W, pady=3)
        ttk.Entry(input_frame, textvariable=self.icon_var).grid(row=6, column=1, sticky=tk.EW, padx=6, pady=3)
        ttk.Button(input_frame, text="Browse...", command=self._pick_icon).grid(row=6, column=2, pady=3)

        node_frame = ttk.Frame(input_frame)
        node_frame.grid(row=7, column=0, columnspan=3, sticky=tk.EW, pady=(6, 0))
        node_frame.columnconfigure(1, weight=1)
        node_frame.columnconfigure(3, weight=1)
        ttk.Label(node_frame, text="nDisplay node").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(node_frame, textvariable=self.node_name_var).grid(row=0, column=1, sticky=tk.EW, padx=(6, 20))
        ttk.Label(node_frame, text="Stage name").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(node_frame, textvariable=self.stage_name_var).grid(row=0, column=3, sticky=tk.EW, padx=(6, 0))

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=1, column=0, sticky=tk.EW, pady=(8, 0))
        ttk.Button(action_frame, text="Generate launcher shortcut", command=self._generate).grid(
            row=0, column=0, sticky=tk.EW
        )
        ttk.Label(action_frame, textvariable=self.status_var).grid(row=1, column=0, sticky=tk.W, pady=(6, 0))

        input_frame.columnconfigure(1, weight=1)
        action_frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def _load_unreal_installations(self) -> None:
        installs = detect_unreal_installs()
        self.detected_engine_paths = [str(i.editor_path) for i in installs]
        self.engine_combo["values"] = self.detected_engine_paths
        if self.detected_engine_paths:
            self.engine_var.set(self.detected_engine_paths[0])
            self.status_var.set(f"Detected {len(self.detected_engine_paths)} Unreal installation(s).")
        else:
            self.status_var.set("No Unreal installations auto-detected. Use Browse to pick UnrealEditor.exe.")

    def _pick_unreal_editor(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select UnrealEditor.exe",
            filetypes=[("Unreal Editor", "UnrealEditor.exe"), ("Executable", "*.exe"), ("All files", "*.*")],
        )
        if selected:
            self.engine_var.set(selected)

    def _pick_uproject(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select .uproject",
            filetypes=[("Unreal Project", "*.uproject"), ("All files", "*.*")],
        )
        if selected:
            self.uproject_var.set(selected)
            self._refresh_maps()

    def _pick_ndisplay(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select .ndisplay config",
            filetypes=[("nDisplay config", "*.ndisplay"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.ndisplay_var.set(selected)

    def _pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder")
        if selected:
            self.output_dir_var.set(selected)

    def _pick_icon(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select shortcut icon",
            filetypes=[("Icon", "*.ico"), ("Executable", "*.exe"), ("All files", "*.*")],
        )
        if selected:
            self.icon_var.set(selected)

    def _refresh_maps(self) -> None:
        uproject = self.uproject_var.get().strip()
        if not uproject:
            self.map_combo["values"] = []
            self.map_var.set("")
            self.status_var.set("Select a .uproject first.")
            return

        uproject_path = Path(uproject)
        if not uproject_path.exists():
            self.map_combo["values"] = []
            self.map_var.set("")
            self.status_var.set(".uproject path does not exist.")
            return

        self.map_values = discover_project_maps(uproject_path)
        self.map_combo["values"] = self.map_values
        if self.map_values:
            self.map_var.set(self.map_values[0])
            self.status_var.set(f"Found {len(self.map_values)} map(s).")
        else:
            self.map_var.set("")
            self.status_var.set("No .umap files found in project Content folder.")

    def _validate_inputs(self) -> tuple[bool, str]:
        engine = Path(self.engine_var.get().strip())
        project = Path(self.uproject_var.get().strip())
        ndisplay = Path(self.ndisplay_var.get().strip())
        output = Path(self.output_dir_var.get().strip())
        map_path = self.map_var.get().strip()
        name = self.launcher_name_var.get().strip()

        if not engine.exists():
            return False, "Please select a valid UnrealEditor.exe path."
        if engine.name.lower() != "unrealeditor.exe":
            return False, "Engine path must point to UnrealEditor.exe."
        if not project.exists() or project.suffix.lower() != ".uproject":
            return False, "Please select a valid .uproject file."
        if not ndisplay.exists():
            return False, "Please select a valid .ndisplay file."
        if not map_path:
            return False, "Please select a map."
        if not name:
            return False, "Please enter a launcher name."
        if any(ch in name for ch in r'\/:*?"<>|'):
            return False, "Launcher name contains invalid Windows filename characters."
        if not output.exists():
            return False, "Output folder does not exist."
        return True, ""

    def _generator_base_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[2]

    def _generate(self) -> None:
        valid, error = self._validate_inputs()
        if not valid:
            messagebox.showerror("Invalid input", error)
            self.status_var.set(error)
            return

        output_dir = Path(self.output_dir_var.get().strip())
        launcher_name = self.launcher_name_var.get().strip()

        profile = LaunchProfile(
            unreal_editor_path=self.engine_var.get().strip(),
            uproject_path=self.uproject_var.get().strip(),
            ndisplay_path=self.ndisplay_var.get().strip(),
            map_path=self.map_var.get().strip(),
            node_name=self.node_name_var.get().strip() or "Node_0",
            stage_name=self.stage_name_var.get().strip() or "Node_0",
        )

        try:
            profile_output_dir = self._generator_base_dir()
            profile_path = write_launch_profile(
                profile,
                output_dir=profile_output_dir,
                profile_name=launcher_name,
            )
            shortcut_path = output_dir / f"{launcher_name}.lnk"
            icon_candidate = Path(self.icon_var.get().strip()) if self.icon_var.get().strip() else None
            create_windows_shortcut(
                shortcut_path=shortcut_path,
                profile_path=profile_path,
                icon_path=icon_candidate,
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Generation failed", str(exc))
            self.status_var.set(f"Generation failed: {exc}")
            return

        messagebox.showinfo(
            "Launcher generated",
            f"Shortcut created:\n{shortcut_path}\n\nProfile created:\n{profile_path}",
        )
        self.status_var.set(f"Generated {shortcut_path.name}")


def main() -> None:
    root = tk.Tk()
    app = GeneratorApp(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()

