from __future__ import annotations

import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .converter import ensure_dxf
from .dxf_reader import PreviewResult, ReadOptions, read_preview_points, read_terrain_points
from .exporters import choose_origin, export_archicad_files


class TerrainCropApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DWG/DXF til Archicad terreng")
        self.root.geometry("1100x780")

        self.file_var = tk.StringVar()
        self.output_var = tk.StringVar(
            value=str(Path.home() / "Downloads" / "borddalen-terrain-selected")
        )
        self.layers_var = tk.StringVar(value="")
        self.sample_distance_var = tk.StringVar(value="20")
        self.include_zero_var = tk.BooleanVar(value=True)
        self.converter_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(
            value="1) Velg DXF-fil. 2) Trykk Vis tegning. 3) Dra en firkant. 4) Eksporter."
        )

        self.preview: PreviewResult | None = None
        self.selected_bbox: tuple[float, float, float, float] | None = None
        self.selection_canvas: tuple[float, float, float, float] | None = None
        self.drag_start: tuple[float, float] | None = None
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_ui()
        self.root.after(100, self._poll_worker)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        file_row = ttk.Frame(frame)
        file_row.pack(fill=tk.X)
        ttk.Label(file_row, text="Fil:").pack(side=tk.LEFT)
        ttk.Entry(file_row, textvariable=self.file_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(file_row, text="Velg DXF/DWG", command=self._choose_file).pack(
            side=tk.LEFT
        )

        output_row = ttk.Frame(frame)
        output_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(output_row, text="Lagre i:").pack(side=tk.LEFT)
        ttk.Entry(output_row, textvariable=self.output_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(output_row, text="Velg mappe", command=self._choose_output).pack(
            side=tk.LEFT
        )

        options = ttk.Frame(frame)
        options.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(options, text="Lagfilter:").pack(side=tk.LEFT)
        ttk.Entry(options, width=22, textvariable=self.layers_var).pack(
            side=tk.LEFT, padx=(4, 12)
        )
        ttk.Label(options, text="Punktavstand:").pack(side=tk.LEFT)
        ttk.Entry(options, width=8, textvariable=self.sample_distance_var).pack(
            side=tk.LEFT, padx=(4, 12)
        )
        ttk.Checkbutton(
            options,
            text="Ta med hoyde 0",
            variable=self.include_zero_var,
        ).pack(side=tk.LEFT)

        converter_row = ttk.Frame(frame)
        converter_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(converter_row, text="ODA exe, hvis DWG:").pack(side=tk.LEFT)
        ttk.Entry(converter_row, textvariable=self.converter_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(converter_row, text="Velg", command=self._choose_converter).pack(
            side=tk.LEFT
        )

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(buttons, text="Vis tegning", command=self._load_preview).pack(
            side=tk.LEFT
        )
        ttk.Button(
            buttons,
            text="Eksporter valgt omrade",
            command=self._export_selection,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="Fjern valg", command=self._clear_selection).pack(
            side=tk.LEFT
        )

        self.canvas = tk.Canvas(frame, background="white", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=(10, 6))
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        self.canvas.bind("<Configure>", lambda _event: self._draw_preview())

        ttk.Label(frame, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X)

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Velg DXF eller DWG",
            filetypes=[("CAD-filer", "*.dxf *.dwg"), ("Alle filer", "*.*")],
        )
        if path:
            self.file_var.set(path)
            default_output = Path(path).with_name(Path(path).stem + "-archicad-area")
            self.output_var.set(str(default_output))

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="Velg mappe for eksport")
        if path:
            self.output_var.set(path)

    def _choose_converter(self) -> None:
        path = filedialog.askopenfilename(
            title="Velg ODAFileConverter.exe",
            filetypes=[("Program", "*.exe"), ("Alle filer", "*.*")],
        )
        if path:
            self.converter_var.set(path)

    def _load_preview(self) -> None:
        try:
            input_path = self._input_path()
            layers = _parse_layers(self.layers_var.get())
            converter = self.converter_var.get().strip() or None
        except ValueError as exc:
            messagebox.showerror("Feil", str(exc))
            return

        self.status_var.set("Leser tegningen. Dette kan ta litt tid...")
        self._run_worker(
            "preview",
            lambda: self._load_preview_worker(input_path, layers, converter),
        )

    def _load_preview_worker(
        self,
        input_path: Path,
        layers: tuple[str, ...],
        converter: str | None,
    ) -> PreviewResult:
        with tempfile.TemporaryDirectory(prefix="dwgterrainarchicad-") as temp_dir:
            dxf_path = ensure_dxf(
                input_path,
                Path(temp_dir),
                converter,
            )
            return read_preview_points(dxf_path, layers=layers)

    def _export_selection(self) -> None:
        if self.selected_bbox is None:
            messagebox.showinfo("Velg omrade", "Dra en firkant i tegningen forst.")
            return

        try:
            input_path = self._input_path()
            output_dir = Path(self.output_var.get()).expanduser()
            sample_distance = float(self.sample_distance_var.get())
            layers = _parse_layers(self.layers_var.get())
            converter = self.converter_var.get().strip() or None
            include_zero = self.include_zero_var.get()
        except ValueError as exc:
            messagebox.showerror("Feil", str(exc))
            return

        bbox = self.selected_bbox
        self.status_var.set("Eksporterer valgt omrade...")
        self._run_worker(
            "export",
            lambda: self._export_worker(
                input_path,
                output_dir,
                sample_distance,
                layers,
                bbox,
                converter,
                include_zero,
            ),
        )

    def _export_worker(
        self,
        input_path: Path,
        output_dir: Path,
        sample_distance: float,
        layers: tuple[str, ...],
        bbox: tuple[float, float, float, float],
        converter: str | None,
        include_zero: bool,
    ) -> tuple[int, dict[str, Path]]:
        with tempfile.TemporaryDirectory(prefix="dwgterrainarchicad-") as temp_dir:
            dxf_path = ensure_dxf(
                input_path,
                Path(temp_dir),
                converter,
            )
            result = read_terrain_points(
                dxf_path,
                ReadOptions(
                    layers=layers,
                    bbox=bbox,
                    sample_distance=sample_distance,
                    include_zero_elevation=include_zero,
                ),
            )
            if not result.points:
                raise ValueError("Ingen punkter funnet i valgt omrade.")
            origin = choose_origin(result.points, "auto")
            outputs = export_archicad_files(
                result.points,
                output_dir,
                input_path.stem,
                origin,
                result.report,
            )
            return len(result.points), outputs

    def _input_path(self) -> Path:
        value = self.file_var.get().strip()
        if not value:
            raise ValueError("Velg en DXF- eller DWG-fil forst.")
        path = Path(value).expanduser()
        if not path.exists():
            raise ValueError(f"Finner ikke filen: {path}")
        return path

    def _run_worker(self, label: str, func) -> None:
        def run() -> None:
            try:
                self.worker_queue.put((label, func()))
            except Exception as exc:
                self.worker_queue.put(("error", exc))

        threading.Thread(target=run, daemon=True).start()

    def _poll_worker(self) -> None:
        try:
            label, payload = self.worker_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_worker)
            return

        if label == "error":
            messagebox.showerror("Feil", str(payload))
            self.status_var.set("Stoppet med feil. Se meldingen over.")
        elif label == "preview":
            self.preview = payload  # type: ignore[assignment]
            self.selected_bbox = None
            self.selection_canvas = None
            self._draw_preview()
            assert self.preview is not None
            self.status_var.set(
                "Tegningen er klar. Dra en firkant rundt omradet du vil eksportere. "
                f"Fant {self.preview.total_points} tegningspunkter."
            )
        elif label == "export":
            count, outputs = payload  # type: ignore[misc]
            self.status_var.set(
                f"Ferdig. Eksporterte {count} punkter til {outputs['archicad_txt']}"
            )
            messagebox.showinfo(
                "Ferdig",
                "Bruk denne filen i Archicad:\n"
                f"{outputs['archicad_txt']}",
            )

        self.root.after(100, self._poll_worker)

    def _draw_preview(self) -> None:
        self.canvas.delete("all")
        if self.preview is None:
            self.canvas.create_text(
                20,
                20,
                anchor=tk.NW,
                text="Velg fil og trykk 'Vis tegning'.",
                fill="gray",
            )
            return

        for x, y in self.preview.points:
            cx, cy = self._to_canvas(x, y)
            self.canvas.create_line(cx, cy, cx + 1, cy, fill="#222222")

        if self.selection_canvas is not None:
            self._draw_selection_rect(*self.selection_canvas)

    def _start_drag(self, event: tk.Event) -> None:
        if self.preview is None:
            return
        self.drag_start = (float(event.x), float(event.y))
        self.selection_canvas = (float(event.x), float(event.y), float(event.x), float(event.y))
        self._draw_preview()

    def _drag(self, event: tk.Event) -> None:
        if self.drag_start is None:
            return
        x0, y0 = self.drag_start
        self.selection_canvas = (x0, y0, float(event.x), float(event.y))
        self._draw_preview()

    def _end_drag(self, event: tk.Event) -> None:
        if self.drag_start is None or self.preview is None:
            return
        x0, y0 = self.drag_start
        x1, y1 = float(event.x), float(event.y)
        self.drag_start = None
        self.selection_canvas = (x0, y0, x1, y1)

        p0 = self._from_canvas(x0, y0)
        p1 = self._from_canvas(x1, y1)
        min_x = min(p0[0], p1[0])
        min_y = min(p0[1], p1[1])
        max_x = max(p0[0], p1[0])
        max_y = max(p0[1], p1[1])
        self.selected_bbox = (min_x, min_y, max_x, max_y)
        self.status_var.set(
            "Omrade valgt. Trykk 'Eksporter valgt omrade' for a lage Archicad-filen."
        )
        self._draw_preview()

    def _clear_selection(self) -> None:
        self.selected_bbox = None
        self.selection_canvas = None
        self._draw_preview()
        self.status_var.set("Valget er fjernet. Dra en ny firkant.")

    def _draw_selection_rect(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            outline="#e00000",
            width=3,
        )

    def _to_canvas(self, x: float, y: float) -> tuple[float, float]:
        min_x, min_y, max_x, max_y = self._bounds()
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        pad = 20
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        scale = min((width - pad * 2) / span_x, (height - pad * 2) / span_y)
        cx = pad + (x - min_x) * scale
        cy = height - pad - (y - min_y) * scale
        return cx, cy

    def _from_canvas(self, cx: float, cy: float) -> tuple[float, float]:
        min_x, min_y, max_x, max_y = self._bounds()
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        pad = 20
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        scale = min((width - pad * 2) / span_x, (height - pad * 2) / span_y)
        x = min_x + (cx - pad) / scale
        y = min_y + (height - pad - cy) / scale
        return (
            min(max(x, min_x), max_x),
            min(max(y, min_y), max_y),
        )

    def _bounds(self) -> tuple[float, float, float, float]:
        assert self.preview is not None
        return self.preview.bounds


def _parse_layers(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def main() -> int:
    root = tk.Tk()
    TerrainCropApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
