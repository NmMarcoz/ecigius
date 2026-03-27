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

# Importamos o nosso motor matemático do workspace
from ecigius_core.generator import generate_signal

import matplotlib
# Configura o matplotlib para rodar em background (não travar a TUI)
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

import webbrowser

class ECGSimulatorApp(App):
    """TUI moderna para simulação de sinais de ECG parametrizável."""
    
    # --- CSS CORRIGIDO PARA RESOLVER OS CORTES ---
    CSS = """
    Screen {
        align: center middle;
    }
    #main-container {
        width: 75; /* Aumentado de 60 para 75 para dar mais respiro lateral */
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
    
    #pqrst-params-grid {
        layout: grid;
        grid-size: 3 2; /* Alterado de 6x2 para 3 colunas confortáveis x 2 linhas */
        grid-gutter: 2; /* Aumentado o gutter para separar os pares */
        margin-top: 1;
        border: solid $secondary;
        padding: 2; /* Aumentado o padding para respiro interno */
        height: auto;
        display: none; /* Escondido por padrão! */
    }
    
    .param-entry {
        layout: horizontal;
        height: 3;
        align: left middle;
    }
    .param-entry Label {
        width: 10; /* Largura fixa e suficiente para rótulos como "P Amp:" */
        content-align: left middle;
    }
    .param-entry Input {
        width: 1fr; /* Input ocupa o restante do espaço na célula do grid */
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

    # O método compose() anterior já estava correto na estrutura de widgets.
    # Vou fornecer o código completo do app.py corrigido para você colar.

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical(id="main-container"):
            # Linha: Ritmo
            with Horizontal():
                yield Label("Ritmo Cardíaco:")
                yield Select(
                    (
                        ("Ritmo Sinusal Normal", "normal"), 
                        ("Fibrilação Atrial", "fa"),
                        ("Personalizado (Manual)", "manual")
                    ),
                    id="rhythm-select",
                    value="manual" # Começa no manual para já vermos os parâmetros
                )
            
            # Linha: Duração
            with Horizontal():
                yield Label("Duração Total (s):")
                yield Input(value="10", id="duration-input", type="number")
            
            # Linha: Diretório
            with Horizontal():
                yield Label("Pasta de Saída:")
                yield Input(placeholder="ex: datasets/", id="outdir-input")

            # Etapa 2: Grid de Parametrização Manual (Fica escondido até escolher "manual")
            with Grid(id="pqrst-params-grid"):
                # Onda P
                with Horizontal(classes="param-entry"):
                    yield Label("P Amp:")
                    yield Input(placeholder="1.2", id="p-amp-input")
                with Horizontal(classes="param-entry"):
                    yield Label("P Larg:")
                    yield Input(placeholder="0.25", id="p-width-input")
                # Onda R
                with Horizontal(classes="param-entry"):
                    yield Label("R Amp:")
                    yield Input(placeholder="30.0", id="r-amp-input")
                with Horizontal(classes="param-entry"):
                    yield Label("R Larg:")
                    yield Input(placeholder="0.1", id="r-width-input")
                # Onda T (Bônus para simular isquemia)
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

    # --- REATIVIDADE DA UI (Inalterada) ---
    def on_mount(self) -> None:
        """Configura o estado inicial da UI após o carregamento."""
        # Se começar no manual, já mostramos o grid
        if self.query_one("#rhythm-select", Select).value == "manual":
            self.query_one("#pqrst-params-grid").display = True

    def on_select_changed(self, event: Select.Changed) -> None:
        """Mostra o painel de parâmetros apenas se o modo 'manual' for selecionado."""
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
        # ... (Lógica de geração inalterada) ...
        log = self.query_one("#log-view", RichLog)
        plot_view = self.query_one("#plot-view", Static)
        
        ui_rhythm = self.query_one("#rhythm-select", Select).value
        duration_str = self.query_one("#duration-input", Input).value
        outdir_str = self.query_one("#outdir-input", Input).value
        
        try:
            duration = float(duration_str)
        except ValueError:
            log.write("[bold red]Erro:[/bold red] Duração inválida.")
            return

        # Lógica de negócio: Se for manual, usamos o motor "normal" e injetamos os overrides
        backend_rhythm = "normal" if ui_rhythm == "manual" else ui_rhythm
        overrides = self.parse_pqrst_overrides() if ui_rhythm == "manual" else None

        log.write(f"Iniciando simulação de {duration}s ('{ui_rhythm}')...")
        
        try:
            # 1. GERAÇÃO MATEMÁTICA (Passando os overrides)
            fs = 256
            t, ecg_signal = generate_signal(
                rhythm=backend_rhythm, 
                duration=duration, 
                fs=fs, 
                hr=60.0,
                pqrst_overrides=overrides
            )
            
            # 2. SALVAMENTO EM DISCO (CSV)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cust_suffix = "_manual" if ui_rhythm == "manual" else ""
            
            # Nomes dos arquivos
            csv_filename = f"ecg_{backend_rhythm}{cust_suffix}_{int(duration)}s_{timestamp}.csv"
            pdf_filename = f"ecg_{backend_rhythm}{cust_suffix}_{int(duration)}s_{timestamp}.pdf"
            
            out_dir = Path(outdir_str) if outdir_str else Path(".")
            if outdir_str:
                out_dir.mkdir(parents=True, exist_ok=True)
                
            csv_filepath = out_dir / csv_filename
            pdf_filepath = out_dir / pdf_filename
                
            # Salva o CSV com o sinal COMPLETO
            with open(csv_filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["time", "amplitude"])
                for time_val, amp_val in zip(t, ecg_signal):
                    writer.writerow([time_val, amp_val])
                    
            log.write(f"[bold green]Dados salvos![/bold green] CSV: [blue]{csv_filepath}[/blue]")

            # ==========================================
            # NOVO: 2.5 SALVAMENTO DO RELATÓRIO EM PDF
            # ==========================================
            # Limita a visualização do PDF para no máximo 10 segundos
            pdf_samples = min(len(t), int(10.0 * fs))
            t_pdf = t[:pdf_samples]
            ecg_pdf = ecg_signal[:pdf_samples]

            fig, ax = plt.subplots(figsize=(12, 4))
            cor_pdf = "cyan" if backend_rhythm == "fa" else "red"
            cor_pdf = "magenta" if ui_rhythm == "manual" else cor_pdf
            
            ax.plot(t_pdf, ecg_pdf, color=cor_pdf, linewidth=1.2)
            ax.set_title(f"Relatório ECG - {ui_rhythm.upper()} (Amostra de {t_pdf[-1]:.1f}s)")
            ax.set_xlabel("Tempo (segundos)")
            ax.set_ylabel("Amplitude (z)")
            ax.grid(True, linestyle='--', alpha=0.7)
            fig.tight_layout()
            
            # Salva e fecha a figura em background
            fig.savefig(pdf_filepath, format='pdf')
            plt.close(fig)
            
            log.write(f"[bold green]Gráfico salvo![/bold green] PDF: [blue]{pdf_filepath}[/blue]")
            
            # Abre o PDF automaticamente no visualizador do sistema (Mac/Win/Linux)
            webbrowser.open(pdf_filepath.absolute().as_uri())

            # 3. RENDERIZAÇÃO NO TERMINAL COM PLOTEXT
            pt.clf() 
            amostras_para_plot = min(len(t), fs * 4) 
            t_view = t[:amostras_para_plot]
            ecg_view = ecg_signal[:amostras_para_plot]

            cor_linha = "cyan" if backend_rhythm == "fa" else "red"
            cor_linha = "magenta" if ui_rhythm == "manual" else cor_linha
            
            # Pega o tamanho REAL do widget descontando bordas e padding
            # Usamos 70 e 20 como fallback caso a tela ainda esteja sendo calculada
            plot_w = plot_view.content_size.width or 70
            plot_h = plot_view.content_size.height or 20
            
            pt.plot(t_view, ecg_view, color=cor_linha, marker="braille")
            pt.title(f"Amostra Visual (Primeiros {len(t_view)/fs:.1f}s) - {ui_rhythm.upper()}")
            
            # Define o tamanho do gráfico para caber perfeitamente na caixa
            pt.plotsize(plot_w, plot_h) 
            pt.canvas_color("black")
            pt.axes_color("black")
            
            ansi_plot = pt.build()
            plot_view.update(Text.from_ansi(ansi_plot))

        except Exception as e:
            log.write(f"[bold red]Erro fatal durante a geração:[/bold red] {str(e)}")

    def parse_pqrst_overrides(self) -> Dict[str, Any]:
        """Lê os Inputs da TUI e constrói o dicionário de overrides."""
        overrides = {}
        
        # Função auxiliar para ler float opcional
        def get_opt_float(input_id: str):
            val = self.query_one(input_id, Input).value.strip()
            if not val: return None
            try: return float(val)
            except ValueError: return None

        # Onda P
        p_amp = get_opt_float("#p-amp-input")
        p_width = get_opt_float("#p-width-input")
        if p_amp is not None or p_width is not None:
            overrides['P'] = {}
            if p_amp is not None: overrides['P']['a'] = p_amp
            if p_width is not None: overrides['P']['b'] = p_width

        # Onda R
        r_amp = get_opt_float("#r-amp-input")
        r_width = get_opt_float("#r-width-input")
        if r_amp is not None or r_width is not None:
            overrides['R'] = {}
            if r_amp is not None: overrides['R']['a'] = r_amp
            if r_width is not None: overrides['R']['b'] = r_width
            
        # Onda T
        t_amp = get_opt_float("#t-amp-input")
        t_width = get_opt_float("#t-width-input")
        if t_amp is not None or t_width is not None:
            overrides['T'] = {}
            if t_amp is not None: overrides['T']['a'] = t_amp
            if t_width is not None: overrides['T']['b'] = t_width
            
        return overrides

def run():
    app = ECGSimulatorApp()
    app.run()

if __name__ == "__main__":
    run()