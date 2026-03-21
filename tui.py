# tui.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Select, Input, RichLog, Label
from textual.containers import Vertical, Horizontal
from core import generate_signal
from pathlib import Path
from datetime import datetime
import csv

class ECGSimulatorApp(App):
    """Uma TUI moderna para simulação de sinais de ECG."""
    
    CSS = """
    Screen {
        align: center middle;
    }
    #main-container {
        width: 60;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
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
    RichLog {
        height: 8;
        border: solid $secondary;
        margin-top: 1;
        background: $panel;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical(id="main-container"):
            # Linha: Ritmo
            with Horizontal():
                yield Label("Ritmo Cardíaco:")
                yield Select(
                    (("Ritmo Sinusal Normal", "normal"), ("Fibrilação Atrial", "fa")),
                    id="rhythm-select",
                    value="fa"
                )
            
            # Linha: Duração
            with Horizontal():
                yield Label("Duração (s):")
                yield Input(value="10", id="duration-input", type="number")
            
            # Linha: Diretório
            with Horizontal():
                yield Label("Pasta de Saída:")
                yield Input(placeholder="ex: datasets/", id="outdir-input")

            yield Button("Gerar Sinal", variant="success", id="generate-btn")
            yield RichLog(id="log-view", highlight=True, markup=True)

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate-btn":
            self.run_generation()

    def run_generation(self) -> None:
        log = self.query_one("#log-view", RichLog)
        
        # Pega os valores dos inputs
        rhythm = self.query_one("#rhythm-select", Select).value
        duration_str = self.query_one("#duration-input", Input).value
        outdir_str = self.query_one("#outdir-input", Input).value
        
        try:
            duration = float(duration_str)
        except ValueError:
            log.write("[bold red]Erro:[/bold red] Duração inválida.")
            return

        log.write(f"Iniciando integração de {duration}s de ritmo '{rhythm}'...")
        
        try:
            # Chama o motor matemático (bloqueia levemente a UI, mas é super rápido)
            t, ecg_signal = generate_signal(rhythm=rhythm, duration=duration, fs=256, hr=60.0)
            log.write("[bold green]Sinal matemático gerado com sucesso![/bold green]")
            
            # Lógica de salvamento
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ecg_{rhythm}_{int(duration)}s_{timestamp}.csv"
            
            if outdir_str:
                out_dir = Path(outdir_str)
                out_dir.mkdir(parents=True, exist_ok=True)
                filepath = out_dir / filename
            else:
                filepath = Path(filename)
                
            with open(filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["time", "amplitude"])
                for time_val, amp_val in zip(t, ecg_signal):
                    writer.writerow([time_val, amp_val])
                    
            log.write(f"[bold blue]Salvo em:[/bold blue] {filepath}")
            
        except Exception as e:
            log.write(f"[bold red]Erro durante a geração:[/bold red] {str(e)}")

if __name__ == "__main__":
    app = ECGSimulatorApp()
    app.run()