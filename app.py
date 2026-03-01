"""
Hertjes PDF → CSV — Grafische gebruikersinterface
==================================================
Start met:  python3 app.py
"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk


class App(tk.Tk):
    DEFAULT_DPI = 300

    def __init__(self):
        super().__init__()
        self.title("Hertjes PDF → CSV")
        self.geometry("680x560")
        self.resizable(True, True)
        self.minsize(540, 480)

        self._cancel_event = threading.Event()
        self._queue: queue.Queue = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------ #
    #  UI opbouw                                                           #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(5, weight=1)  # log groeit mee

        pad = {"padx": 12, "pady": 6}

        # ── PDF bestand ──────────────────────────────────────────────── #
        tk.Label(self, text="PDF bestand:", anchor="w").grid(
            row=0, column=0, sticky="w", **pad
        )
        self.pdf_var = tk.StringVar()
        tk.Entry(self, textvariable=self.pdf_var).grid(
            row=0, column=1, sticky="ew", **pad
        )
        tk.Button(self, text="Bladeren…", command=self._browse_pdf).grid(
            row=0, column=2, **pad
        )

        # ── Output map ───────────────────────────────────────────────── #
        tk.Label(self, text="Output map:", anchor="w").grid(
            row=1, column=0, sticky="w", **pad
        )
        self.output_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        tk.Entry(self, textvariable=self.output_var).grid(
            row=1, column=1, sticky="ew", **pad
        )
        tk.Button(self, text="Bladeren…", command=self._browse_output).grid(
            row=1, column=2, **pad
        )

        # ── Opties ───────────────────────────────────────────────────── #
        opts = tk.LabelFrame(self, text="Opties", padx=8, pady=6)
        opts.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=4)

        self.eerste_leeg_var = tk.BooleanVar()
        tk.Checkbutton(
            opts, text="Eerste pagina is leeg (verschuif paginanummering)",
            variable=self.eerste_leeg_var,
        ).pack(side="left")

        tk.Label(opts, text="  DPI:").pack(side="left")
        self.dpi_var = tk.IntVar(value=self.DEFAULT_DPI)
        tk.Spinbox(
            opts, from_=150, to=600, increment=50,
            textvariable=self.dpi_var, width=6,
        ).pack(side="left", padx=4)

        # ── Voortgangsbalk ────────────────────────────────────────────── #
        self.progress_label = tk.Label(self, text="", anchor="w", fg="#555")
        self.progress_label.grid(row=3, column=0, columnspan=3, sticky="w", padx=12)

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 4)
        )

        # ── Status log ───────────────────────────────────────────────── #
        self.log = scrolledtext.ScrolledText(
            self, height=10, state="disabled", wrap="word",
            font=("Menlo", 11), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white",
        )
        self.log.grid(
            row=5, column=0, columnspan=3, sticky="nsew", padx=12, pady=(0, 6)
        )
        # kleur-tags
        self.log.tag_config("ok",    foreground="#6dde6d")
        self.log.tag_config("warn",  foreground="#e8cb66")
        self.log.tag_config("err",   foreground="#f44747")
        self.log.tag_config("info",  foreground="#9cdcfe")
        self.log.tag_config("dim",   foreground="#888888")

        # ── Knoppen ──────────────────────────────────────────────────── #
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)

        self.maak_btn = tk.Button(
            btn_frame, text="Maak CSV", command=self._start,
            bg="#2d7d2d", fg="white", padx=24, pady=8,
            font=(None, 13, "bold"), relief="flat", cursor="hand2",
        )
        self.maak_btn.pack(side="left", padx=10)

        self.annuleer_btn = tk.Button(
            btn_frame, text="Annuleer", command=self._cancel,
            bg="#c0392b", fg="white", padx=24, pady=8,
            font=(None, 13), relief="flat", cursor="hand2", state="disabled",
        )
        self.annuleer_btn.pack(side="left", padx=10)

    # ------------------------------------------------------------------ #
    #  Bestand / map selectie                                              #
    # ------------------------------------------------------------------ #

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Selecteer PDF",
            filetypes=[("PDF bestanden", "*.pdf"), ("Alle bestanden", "*.*")],
        )
        if path:
            self.pdf_var.set(path)
            # Stel output map automatisch in op map van de PDF
            pdf_dir = str(Path(path).parent)
            self.output_var.set(pdf_dir)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Selecteer output map")
        if path:
            self.output_var.set(path)

    # ------------------------------------------------------------------ #
    #  Log helpers                                                         #
    # ------------------------------------------------------------------ #

    def _log(self, msg: str, tag: str = ""):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    # ------------------------------------------------------------------ #
    #  Knoppen actie                                                       #
    # ------------------------------------------------------------------ #

    def _set_running(self, running: bool):
        self.maak_btn.config(state="disabled" if running else "normal")
        self.annuleer_btn.config(state="normal" if running else "disabled")

    def _start(self):
        pdf = self.pdf_var.get().strip()
        output_dir = self.output_var.get().strip()

        if not pdf:
            self._log_clear()
            self._log("⚠  Selecteer eerst een PDF bestand.", "warn")
            return

        pdf_path = Path(pdf)
        if not pdf_path.exists():
            self._log_clear()
            self._log(f"⚠  PDF niet gevonden: {pdf_path}", "warn")
            return

        output_path = Path(output_dir) / (pdf_path.stem + ".csv")

        self._cancel_event.clear()
        self.progress["value"] = 0
        self.progress_label.config(text="")
        self._log_clear()
        self._log(f"▶  PDF:    {pdf_path.name}", "info")
        self._log(f"   Output: {output_path}", "dim")
        self._set_running(True)

        threading.Thread(
            target=self._run_ocr,
            args=(pdf_path, output_path, self.eerste_leeg_var.get(), self.dpi_var.get()),
            daemon=True,
        ).start()

    def _cancel(self):
        self._cancel_event.set()
        self._log("⛔  Annuleren na huidige pagina...", "warn")

    # ------------------------------------------------------------------ #
    #  Achtergrond-thread: OCR uitvoeren                                   #
    # ------------------------------------------------------------------ #

    def _run_ocr(self, pdf_path: Path, output_path: Path,
                 eerste_pagina_leeg: bool, dpi: int):
        try:
            from pdf_to_csv import parse_ocr_text, pdf_to_ocr_text, schrijf_csv
        except ImportError as e:
            self._queue.put(("log", f"✖  Import fout: {e}", "err"))
            self._queue.put(("done", False))
            return

        def progress(msg: str, pct):
            self._queue.put(("progress", msg, pct))

        # Stap 1: OCR
        try:
            ocr_text = pdf_to_ocr_text(
                pdf_path, dpi=dpi, taal="nld+eng",
                progress_callback=progress,
                cancel_event=self._cancel_event,
            )
        except Exception as e:
            self._queue.put(("log", f"✖  Fout tijdens OCR: {e}", "err"))
            self._queue.put(("done", False))
            return

        if ocr_text is None or self._cancel_event.is_set():
            self._queue.put(("log", "⛔  Geannuleerd.", "warn"))
            self._queue.put(("done", False))
            return

        # Stap 2: parsen
        self._queue.put(("progress", "Tekst parsen...", 92))
        try:
            opdrachten = parse_ocr_text(ocr_text, eerste_pagina_leeg=eerste_pagina_leeg)
        except Exception as e:
            self._queue.put(("log", f"✖  Fout bij parsen: {e}", "err"))
            self._queue.put(("done", False))
            return

        if not opdrachten:
            self._queue.put((
                "log",
                "⚠  Geen opdrachten gevonden. Controleer of de PDF het verwachte formaat heeft.",
                "warn",
            ))
            self._queue.put(("done", False))
            return

        self._queue.put(("log", f"   {len(opdrachten)} opdrachten herkend.", "dim"))

        # Stap 3: CSV schrijven
        self._queue.put(("progress", "CSV opslaan...", 96))
        try:
            schrijf_csv(opdrachten, output_path)
        except Exception as e:
            self._queue.put(("log", f"✖  Fout bij schrijven CSV: {e}", "err"))
            self._queue.put(("done", False))
            return

        self._queue.put((
            "log",
            f"✅  Klaar! CSV opgeslagen:\n    {output_path}",
            "ok",
        ))
        self._queue.put(("progress", "Klaar", 100))
        self._queue.put(("done", True))

    # ------------------------------------------------------------------ #
    #  Queue polling (UI-thread)                                           #
    # ------------------------------------------------------------------ #

    def _poll_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]

                if kind == "log":
                    _, msg, tag = item
                    self._log(msg, tag)

                elif kind == "progress":
                    _, msg, pct = item
                    if msg:
                        self.progress_label.config(text=msg)
                    if pct is not None:
                        self.progress["value"] = pct

                elif kind == "done":
                    self._set_running(False)
                    self.progress_label.config(text="")

        except queue.Empty:
            pass

        self.after(80, self._poll_queue)


# ------------------------------------------------------------------ #
#  Start                                                               #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    app = App()
    app.mainloop()
