# packages/tui/src/ecigius_tui/app.py

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Select, Input, RichLog, Label, Static
from textual.containers import Vertical, Horizontal, Grid, Container
from rich.text import Text
import plotext as pt
import csv
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import webbrowser

from ecigius_core.generator import generate_signal
from ecigius_core.validation import ECGValidator

class ECGSimulatorApp(App):
    """TUI Final do Ecigius: Simulação, Ruídos e Benchmarking."""
    
    CSS = """
    Screen { align: center middle; }
    #main-container {
        width: 85;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    .section-title { text-style: bold; color: $accent; margin-top: 1; margin-bottom: 0; }
    Horizontal { height: auto; margin-bottom: 1; }
    Label { width: 20; content-align: left middle; }
    
    /* Grid de Ruídos */
    #noise-params-grid {
        layout: grid;
        grid-size: 3 1;
        grid-gutter: 2;
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
        height: 5;
    }
    
    /* Grid Manual PQRST */
    #pqrst-params-grid { 
        layout: grid;
        grid-size: 3 2; 
        grid-gutter: 1;
        display: none; 
        margin-top: 1;
        border: solid $secondary;
        padding: 1;
        height: 8;
    }

    .cell {
        layout: horizontal;
        align: left middle;
    }
    .cell Label { width: 8; }
    .cell Input { width: 1fr; height: 3; }

    #benchmark-container {
        border: double $warning;
        padding: 1;
        margin-top: 1;
        background: $panel;
        display: none;
    }

    RichLog { height: 6; border: solid $secondary; margin-top: 1; }
    Static#plot-view {
        height: 20;
        border: solid $accent;
        background: black;
        color: lime;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main-container"):
            yield Label("🧬 Configurações Clínicas", classes="section-title")
            with Horizontal():
                yield Label("Ritmo:")
                yield Select([
                    ("Sinusal Normal", "normal"), 
                    ("Fibrilação Atrial", "fa"), 
                    ("Manual", "manual")
                ], id="rhythm-select", value="normal")
            
            with Horizontal():
                yield Label("FC Média | Var:")
                yield Input(value="60.0", id="hr-input")
                yield Input(value="1.0", id="hr-std-input")

            yield Label("🌪️ Artefatos e Ruídos", classes="section-title")
            with Grid(id="noise-params-grid"):
                with Horizontal(classes="cell"):
                    yield Label("Resp:")
                    yield Input(value="0.0", id="bw-input")
                with Horizontal(classes="cell"):
                    yield Label("60Hz:")
                    yield Input(value="0.0", id="pl-input")
                with Horizontal(classes="cell"):
                    yield Label("Gauss:")
                    yield Input(value="0.0", id="noise-input")

            yield Label("📊 Validação (Benchmark)", classes="section-title")
            with Horizontal():
                yield Label("Ref. CSV:")
                yield Input(placeholder="./files/template_mitbih_201_fa.csv", id="ref-csv-input")
            with Horizontal():
                yield Label("Beats p/ Val:")
                yield Input(value="3", id="val-beats-input")

            with Vertical(id="benchmark-container"):
                yield Label("📋 RESULTADO DO BENCHMARK")
                yield Static("", id="bench-results")

            with Grid(id="pqrst-params-grid"):
                with Horizontal(classes="cell"):
                    yield Label("P Amp:")
                    yield Input(placeholder="1.2", id="p-amp-input")
                with Horizontal(classes="cell"):
                    yield Label("P Larg:")
                    yield Input(placeholder="0.25", id="p-width-input")
                with Horizontal(classes="cell"):
                    yield Label("R Amp:")
                    yield Input(placeholder="30.0", id="r-amp-input")
                with Horizontal(classes="cell"):
                    yield Label("R Larg:")
                    yield Input(placeholder="0.1", id="r-width-input")
                with Horizontal(classes="cell"):
                    yield Label("T Amp:")
                    yield Input(placeholder="0.75", id="t-amp-input")
                with Horizontal(classes="cell"):
                    yield Label("T Larg:")
                    yield Input(placeholder="0.4", id="t-width-input")

            yield Button("Gerar, Validar e Plotar", variant="success", id="generate-btn")
            yield RichLog(id="log-view")
            yield Static("Aguardando comando...", id="plot-view")
        yield Footer()

    def on_mount(self) -> None:
        self.update_manual_grid(self.query_one("#rhythm-select", Select).value)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "rhythm-select":
            self.update_manual_grid(event.value)

    def update_manual_grid(self, value: str) -> None:
        grid = self.query_one("#pqrst-params-grid")
        grid.display = (value == "manual")

    def parse_pqrst_overrides(self) -> Dict[str, Any]:
        overrides = {}
        def get_val(id: str):
            v = self.query_one(id, Input).value.strip()
            return float(v) if v else None
        p_a, p_b = get_val("#p-amp-input"), get_val("#p-width-input")
        if p_a or p_b: overrides['P'] = {'a': p_a, 'b': p_b}
        r_a, r_b = get_val("#r-amp-input"), get_val("#r-width-input")
        if r_a or r_b: overrides['R'] = {'a': r_a, 'b': r_b}
        t_a, t_b = get_val("#t-amp-input"), get_val("#t-width-input")
        if t_a or t_b: overrides['T'] = {'a': t_a, 'b': t_b}
        return overrides

    def run_full_pipeline(self) -> None:
        log = self.query_one("#log-view", RichLog)
        plot_view = self.query_one("#plot-view", Static)
        bench_cont = self.query_one("#benchmark-container")
        bench_res = self.query_one("#bench-results")
        
        try:
            ui_rhythm = self.query_one("#rhythm-select", Select).value
            hr = float(self.query_one("#hr-input").value)
            hr_std = float(self.query_one("#hr-std-input").value)
            bw = float(self.query_one("#bw-input").value or 0)
            pl = float(self.query_one("#pl-input").value or 0)
            noise = float(self.query_one("#noise-input").value or 0)
            ref_path = self.query_one("#ref-csv-input").value
            val_beats = int(self.query_one("#val-beats-input").value or 1)

            backend_rhythm = "normal" if ui_rhythm == "manual" else ui_rhythm
            overrides = self.parse_pqrst_overrides() if ui_rhythm == "manual" else None

            fs = 360 
            duration = 10.0

            t, ecg = generate_signal(
                backend_rhythm, duration, fs, hr, hr_std, 
                pqrst_overrides=overrides, bw_amp=bw, pl_amp=pl, noise_std=noise
            )
            
            log.write(f"Sinal gerado com sucesso.")

            if ref_path and Path(ref_path).exists():
                ref_data = np.loadtxt(ref_path, delimiter=',', skiprows=1)
                metrics = ECGValidator.validate(ecg, ref_data[:, 1], fs=fs, num_beats=val_beats)
                dtw_s = "✅" if metrics['dtw_distance'] < 0.15 else "❌"
                prd_s = "✅" if metrics['prd_percent'] < 50.0 else "❌"
                
                res_text = Text.assemble(
                    (f"{dtw_s} DTW: {metrics['dtw_distance']}  ", "bold green" if dtw_s=="✅" else "bold red"),
                    (f"{prd_s} PRD: {metrics['prd_percent']}%  ", "bold green" if prd_s=="✅" else "bold red"),
                    (f"RMSE: {metrics['rmse']}", "italic")
                )
                bench_res.update(res_text)
                bench_cont.display = True
            else:
                bench_cont.display = False

            pt.clf()
            pt.plotsize(plot_view.content_size.width or 75, plot_view.content_size.height or 20)
            pt.plot(t[:fs*4], ecg[:fs*4], color="cyan", marker="braille")
            pt.title(f"Preview {ui_rhythm.upper()}")
            plot_view.update(Text.from_ansi(pt.build()))

        except Exception as e:
            log.write(f"[bold red]Erro:[/bold red] {str(e)}")

def run():
    ECGSimulatorApp().run()

if __name__ == "__main__":
    run()