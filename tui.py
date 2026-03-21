from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Select, Input, RichLog, Label, Static
from textual.containers import Vertical, Horizontal
from rich.text import Text
import plotext as pt
import csv
from pathlib import Path
from datetime import datetime

# Importamos o nosso motor matemático isolado
from core import generate_signal

class ECGSimulatorApp(App):
    """Uma TUI moderna para simulação de sinais de ECG com Plotagem Nativa."""
    
    CSS = """
    Screen {
        align: center top;
        padding: 1;
    }
    #controls-container {
        height: auto;
        border: round $primary;
        padding: 1;
        margin-bottom: 1;
    }
    Horizontal {
        height: auto;
        margin-bottom: 1;
    }
    Label {
        width: 20;
        content-align: left middle;
    }
    Select, Input {
        width: 1fr;
    }
    Button {
        width: 100%;
        margin-top: 1;
    }
    #log-view {
        height: 5;
        border: solid $secondary;
        margin-bottom: 1;
    }
    #plot-view {
        height: 1fr;
        min-height: 22;
        border: solid $accent;
        padding: 1;
        content-align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        # Painel de Controles
        with Vertical(id="controls-container"):
            with Horizontal():
                yield Label("Ritmo Cardíaco:")
                yield Select(
                    (("Ritmo Sinusal Normal", "normal"), ("Fibrilação Atrial", "fa")),
                    id="rhythm-select",
                    value="fa"
                )
            with Horizontal():
                yield Label("Duração Total (s):")
                yield Input(value="10", id="duration-input", type="number")
            with Horizontal():
                yield Label("Pasta de Saída:")
                yield Input(placeholder="ex: datasets/", id="outdir-input")

            yield Button("Gerar e Plotar Sinal", variant="success", id="generate-btn")
        
        # Painéis de Saída
        yield RichLog(id="log-view", highlight=True, markup=True)
        # O Static vai receber a string em Braille gerada pelo plotext
        yield Static("Aguardando geração do sinal...", id="plot-view") 

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate-btn":
            self.run_generation()

    def run_generation(self) -> None:
        log = self.query_one("#log-view", RichLog)
        plot_view = self.query_one("#plot-view", Static)
        
        rhythm = self.query_one("#rhythm-select", Select).value
        duration_str = self.query_one("#duration-input", Input).value
        outdir_str = self.query_one("#outdir-input", Input).value
        
        try:
            duration = float(duration_str)
        except ValueError:
            log.write("[bold red]Erro:[/bold red] Duração inválida.")
            return

        log.write(f"Calculando {duration}s de EDOs para o ritmo '{rhythm}'...")
        
        try:
            # 1. GERAÇÃO MATEMÁTICA
            fs = 256
            t, ecg_signal = generate_signal(rhythm=rhythm, duration=duration, fs=fs, hr=60.0)
            
            # 2. SALVAMENTO EM DISCO (Salva o sinal completo)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ecg_{rhythm}_{int(duration)}s_{timestamp}.csv"
            
            out_dir = Path(outdir_str) if outdir_str else Path(".")
            if outdir_str:
                out_dir.mkdir(parents=True, exist_ok=True)
            filepath = out_dir / filename
                
            with open(filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["time", "amplitude"])
                for time_val, amp_val in zip(t, ecg_signal):
                    writer.writerow([time_val, amp_val])
                    
            log.write(f"[bold green]Sucesso![/bold green] Arquivo completo salvo em: [blue]{filepath}[/blue]")

            # 3. RENDERIZAÇÃO NO TERMINAL COM PLOTEXT
            pt.clf() # Limpa o plot anterior
            
            # Truque de UI: Plotamos no máximo os primeiros 4 segundos. 
            # Se tentarmos plotar 30s de ECG no espaço apertado do terminal, vira um borrão ilegível.
            amostras_para_plot = min(len(t), fs * 4) 
            t_view = t[:amostras_para_plot]
            ecg_view = ecg_signal[:amostras_para_plot]

            cor_linha = "cyan" if rhythm == "fa" else "red"
            pt.plot(t_view, ecg_view, color=cor_linha, marker="braille")
            pt.title(f"Amostra Visul (Primeiros {len(t_view)/fs:.1f}s) - {rhythm.upper()}")
            pt.plotsize(100, 20) # Força um tamanho que caiba bem na widget
            pt.canvas_color("black")
            pt.axes_color("black")
            
            # Extrai a string com os códigos ANSI de cor e passa para a interface
            ansi_plot = pt.build()
            plot_view.update(Text.from_ansi(ansi_plot))

        except Exception as e:
            log.write(f"[bold red]Erro fatal:[/bold red] {str(e)}")

if __name__ == "__main__":
    app = ECGSimulatorApp()
    app.run()