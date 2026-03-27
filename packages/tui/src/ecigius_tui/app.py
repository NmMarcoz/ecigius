# packages/tui/src/ecigius_tui/app.py

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Select, Input, RichLog, Label, Static
from textual.containers import Vertical, Horizontal, Grid
from rich.text import Text
import plotext as pt
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import webbrowser

from ecigius_core.generator import generate_signal

class ECGSimulatorApp(App):
    """TUI moderna para simulação de sinais de ECG parametrizável e com ruídos."""
    
    CSS = """
    Screen {
        align: center middle;
    }
    #main-container {
        width: 80; /* Aumentei um pouquinho para acomodar as 3 colunas de ruído */
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    Horizontal {
        height: auto;
        margin-bottom: 1;
    }
    .section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }
    Label {
        width: 22; 
        content-align: left middle;
    }
    Select, Input {
        width: 1fr;
    }
    
    #noise-params-grid, #pqrst-params-grid {
        layout: grid;
        grid-size: 3 2; 
        grid-gutter: 2; 
        border: solid $secondary;
        padding: 1 2; 
        height: auto;
    }
    
    #pqrst-params-grid {
        display: none; /* Só aparece no modo manual */
        margin-top: 1;
    }

    #noise-params-grid {
        grid-size: 3 1; /* 3 colunas, 1 linha para os ruídos */
        margin-bottom: 1;
    }
    
    .param-entry {
        layout: horizontal;
        height: 3;
        align: left middle;
    }
    .param-entry Label {
        width: 12; 
        content-align: left middle;
    }
    .param-entry Input {
        width: 1fr; 
    }

    Button {
        width: 100%;
        margin-top: 1;
    }
    RichLog {
        height: 8;
        border: solid $secondary;
        margin-top: 1;
        background: $panel;
    }
    Static#plot-view {
        height: 1fr;
        min-height: 22;
        border: solid $accent;
        padding: 1;
        content-align: center middle;
        background: black;
        color: lime;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical(id="main-container"):
            # --- BLOCO: CLÍNICO ---
            yield Label("Configurações Clínicas", classes="section-title")
            with Horizontal():
                yield Label("Ritmo Cardíaco:")
                yield Select(
                    (
                        ("Ritmo Sinusal Normal", "normal"), 
                        ("Fibrilação Atrial", "fa"),
                        ("Personalizado (Manual)", "manual")
                    ),
                    id="rhythm-select",
                    value="normal"
                )
            with Horizontal():
                yield Label("FC Média (BPM):")
                yield Input(value="60.0", id="hr-input")
            with Horizontal():
                yield Label("Variabilidade (BPM):")
                yield Input(value="1.0", id="hr-std-input", placeholder="Ex: 15.0 para alta variância")

            # --- BLOCO: RUÍDOS (ETAPA 5) ---
            yield Label("Artefatos e Ruídos (Opcional)", classes="section-title")
            with Grid(id="noise-params-grid"):
                with Horizontal(classes="param-entry"):
                    yield Label("Respiração:")
                    yield Input(value="0.0", id="bw-input", placeholder="Ex: 0.2")
                with Horizontal(classes="param-entry"):
                    yield Label("Rede (60Hz):")
                    yield Input(value="0.0", id="pl-input", placeholder="Ex: 0.05")
                with Horizontal(classes="param-entry"):
                    yield Label("Térmico (Std):")
                    yield Input(value="0.0", id="noise-input", placeholder="Ex: 0.03")

            # --- BLOCO: EXPORTAÇÃO ---
            with Horizontal():
                yield Label("Duração Total (s):")
                yield Input(value="10", id="duration-input", type="number")
            with Horizontal():
                yield Label("Pasta de Saída:")
                yield Input(placeholder="ex: datasets/", id="outdir-input")

            # --- BLOCO: MANUAL (Escondido) ---
            with Grid(id="pqrst-params-grid"):
                with Horizontal(classes="param-entry"):
                    yield Label("P Amp:")
                    yield Input(placeholder="1.2", id="p-amp-input")
                with Horizontal(classes="param-entry"):
                    yield Label("P Larg:")
                    yield Input(placeholder="0.25", id="p-width-input")
                with Horizontal(classes="param-entry"):
                    yield Label("R Amp:")
                    yield Input(placeholder="30.0", id="r-amp-input")
                with Horizontal(classes="param-entry"):
                    yield Label("R Larg:")
                    yield Input(placeholder="0.1", id="r-width-input")
                with Horizontal(classes="param-entry"):
                    yield Label("T Amp:")
                    yield Input(placeholder="0.75", id="t-amp-input")
                with Horizontal(classes="param-entry"):
                    yield Label("T Larg:")
                    yield Input(placeholder="0.4", id="t-width-input")

            yield Button("Gerar e Plotar Sinal", variant="success", id="generate-btn")
            yield RichLog(id="log-view", highlight=True, markup=True)
            yield Static("Aguardando geração do sinal...", id="plot-view") 

        yield Footer()

    def on_mount(self) -> None:
        if self.query_one("#rhythm-select", Select).value == "manual":
            self.query_one("#pqrst-params-grid").display = True

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "rhythm-select":
            grid = self.query_one("#pqrst-params-grid")
            if event.value == "manual":
                grid.display = True
                self.query_one("#log-view", RichLog).write("[italic]Modo Manual ativado. Baseado no ritmo Sinusal Normal.[/italic]")
            else:
                grid.display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate-btn":
            self.run_generation()

    def run_generation(self) -> None:
        log = self.query_one("#log-view", RichLog)
        plot_view = self.query_one("#plot-view", Static)
        
        ui_rhythm = self.query_one("#rhythm-select", Select).value
        duration_str = self.query_one("#duration-input", Input).value
        outdir_str = self.query_one("#outdir-input", Input).value
        
        try:
            duration = float(duration_str)
            hr_val = float(self.query_one("#hr-input", Input).value)
            hr_std_val = float(self.query_one("#hr-std-input", Input).value)
            
            # Lê os novos campos de ruído (usa 0.0 se estiver vazio)
            bw_val = float(self.query_one("#bw-input", Input).value or 0.0)
            pl_val = float(self.query_one("#pl-input", Input).value or 0.0)
            noise_val = float(self.query_one("#noise-input", Input).value or 0.0)
            
        except ValueError:
            log.write("[bold red]Erro:[/bold red] Verifique se os números digitados são válidos.")
            return

        backend_rhythm = "normal" if ui_rhythm == "manual" else ui_rhythm
        overrides = self.parse_pqrst_overrides() if ui_rhythm == "manual" else None

        log.write(f"Iniciando simulação de {duration}s ('{ui_rhythm}'). FC: {hr_val} | Var: {hr_std_val}")
        if bw_val > 0 or pl_val > 0 or noise_val > 0:
            log.write(f"Injetando ruídos -> Respiração: {bw_val}, Rede: {pl_val}, Térmico: {noise_val}")
        
        try:
            fs = 256
            t, ecg_signal = generate_signal(
                rhythm=backend_rhythm, 
                duration=duration, 
                fs=fs, 
                hr=hr_val,
                hr_std=hr_std_val,
                pqrst_overrides=overrides,
                bw_amp=bw_val,
                pl_amp=pl_val,
                noise_std=noise_val
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cust_suffix = "_manual" if ui_rhythm == "manual" else ""
            
            csv_filename = f"ecg_{backend_rhythm}{cust_suffix}_{int(duration)}s_{timestamp}.csv"
            pdf_filename = f"ecg_{backend_rhythm}{cust_suffix}_{int(duration)}s_{timestamp}.pdf"
            
            out_dir = Path(outdir_str) if outdir_str else Path(".")
            if outdir_str:
                out_dir.mkdir(parents=True, exist_ok=True)
                
            csv_filepath = out_dir / csv_filename
            pdf_filepath = out_dir / pdf_filename
                
            with open(csv_filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["time", "amplitude"])
                for time_val, amp_val in zip(t, ecg_signal):
                    writer.writerow([time_val, amp_val])
                    
            log.write(f"[bold green]Dados guardados![/bold green] CSV: [blue]{csv_filepath}[/blue]")

            # Geração do PDF
            pdf_samples = min(len(t), int(10.0 * fs))
            t_pdf = t[:pdf_samples]
            ecg_pdf = ecg_signal[:pdf_samples]

            fig, ax = plt.subplots(figsize=(12, 4))
            cor_pdf = "cyan" if backend_rhythm == "fa" else "red"
            cor_pdf = "magenta" if ui_rhythm == "manual" else cor_pdf
            
            ax.plot(t_pdf, ecg_pdf, color=cor_pdf, linewidth=1.2)
            ax.set_title(f"Relatório ECG - {ui_rhythm.upper()} (FC: {hr_val} BPM)")
            ax.set_xlabel("Tempo (segundos)")
            ax.set_ylabel("Amplitude (z)")
            ax.grid(True, linestyle='--', alpha=0.7)
            fig.tight_layout()
            
            fig.savefig(pdf_filepath, format='pdf')
            plt.close(fig)
            
            log.write(f"[bold green]Gráfico gerado![/bold green] PDF: [blue]{pdf_filepath}[/blue]")
            
            webbrowser.open(pdf_filepath.absolute().as_uri())

            pt.clf() 
            amostras_para_plot = min(len(t), fs * 4) 
            t_view = t[:amostras_para_plot]
            ecg_view = ecg_signal[:amostras_para_plot]

            cor_linha = "cyan" if backend_rhythm == "fa" else "red"
            cor_linha = "magenta" if ui_rhythm == "manual" else cor_linha 
            
            plot_w = plot_view.content_size.width or 70
            plot_h = plot_view.content_size.height or 20
            
            pt.plot(t_view, ecg_view, color=cor_linha, marker="braille")
            pt.title(f"Amostra Visual (Primeiros {len(t_view)/fs:.1f}s) - {ui_rhythm.upper()}")
            
            pt.plotsize(plot_w, plot_h) 
            pt.canvas_color("black")
            pt.axes_color("black")
            
            ansi_plot = pt.build()
            plot_view.update(Text.from_ansi(ansi_plot))

        except Exception as e:
            log.write(f"[bold red]Erro fatal durante a geração:[/bold red] {str(e)}")

    def parse_pqrst_overrides(self) -> Dict[str, Any]:
        overrides = {}
        def get_opt_float(input_id: str):
            val = self.query_one(input_id, Input).value.strip()
            if not val: return None
            try: return float(val)
            except ValueError: return None

        p_amp = get_opt_float("#p-amp-input")
        p_width = get_opt_float("#p-width-input")
        if p_amp is not None or p_width is not None:
            overrides['P'] = {'a': p_amp, 'b': p_width}

        r_amp = get_opt_float("#r-amp-input")
        r_width = get_opt_float("#r-width-input")
        if r_amp is not None or r_width is not None:
            overrides['R'] = {'a': r_amp, 'b': r_width}
            
        t_amp = get_opt_float("#t-amp-input")
        t_width = get_opt_float("#t-width-input")
        if t_amp is not None or t_width is not None:
            overrides['T'] = {'a': t_amp, 'b': t_width}
            
        return overrides

def run():
    app = ECGSimulatorApp()
    app.run()

if __name__ == "__main__":
    run()