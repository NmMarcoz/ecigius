# packages/cli/src/ecigius_cli/main.py
import typer
import csv
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from typing import Optional

# Importamos o motor matemático do workspace
from ecigius_core import generate_signal

app = typer.Typer(help="Simulador de ECG baseado no modelo de McSharry (CLI)")

@app.command()
def generate(
    # Argumentos Base
    rhythm: str = typer.Option("normal", "--rhythm", "-r", help="Tipo de ritmo: 'normal' ou 'fa'"),
    duration: float = typer.Option(10.0, "--duration", "-d", help="Duração do sinal em segundos"),
    fs: int = typer.Option(256, "--fs", "-f", help="Frequência de amostragem em Hz"),
    hr: float = typer.Option(60.0, "--hr", help="Frequência cardíaca (apenas ritmo normal)"),
    
    # Parâmetros Morfológicos (Etapa 2 - Overrides)
    p_amp: Optional[float] = typer.Option(None, help="Override Amplitude Onda P (default: 1.2)"),
    p_width: Optional[float] = typer.Option(None, help="Override Largura Onda P (default: 0.25)"),
    r_amp: Optional[float] = typer.Option(None, help="Override Amplitude Onda R (QRS) (default: 30.0)"),
    r_width: Optional[float] = typer.Option(None, help="Override Largura Onda R (QRS) (default: 0.1)"),
    
    # I/O
    plot: bool = typer.Option(True, "--plot/--no-plot", help="Exibe o gráfico após gerar"),
    output: str = typer.Option(None, "--output", "-o", help="Nome do arquivo (ex: teste.csv)"),
    out_dir: Path = typer.Option(None, "--out-dir", help="Pasta de destino (ex: datasets/)")
):
    """
    Gera um sinal sintético de ECG parametrizável e exporta os dados.
    """
    typer.secho(f"Gerando {duration}s de ECG no ritmo '{rhythm.upper()}' a {fs}Hz...", fg=typer.colors.CYAN)
    
    # Constrói o dicionário de overrides morfológicos da Etapa 2
    overrides = {}
    if p_amp is not None or p_width is not None:
        overrides['P'] = {}
        if p_amp is not None: overrides['P']['a'] = p_amp
        if p_width is not None: overrides['P']['b'] = p_width
        
    if r_amp is not None or r_width is not None:
        overrides['R'] = {}
        if r_amp is not None: overrides['R']['a'] = r_amp
        if r_width is not None: overrides['R']['b'] = r_width

    try:
        # Passa os overrides para o motor
        t, ecg_signal = generate_signal(
            rhythm=rhythm, 
            duration=duration, 
            fs=fs, 
            hr=hr,
            pqrst_overrides=overrides if overrides else None
        )
    except Exception as e:
        typer.secho(f"Erro na geração matemática: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    # --- LÓGICA DE SALVAMENTO (Inalterada) ---
    if output or out_dir:
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ecg_{rhythm}_{int(duration)}s_{timestamp}.csv"
        else:
            filename = output

        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            filepath = out_dir / filename
        else:
            filepath = Path(filename)

        try:
            with open(filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["time", "amplitude"])
                for time_val, amp_val in zip(t, ecg_signal):
                    writer.writerow([time_val, amp_val])
            typer.secho(f"Sinal salvo com sucesso em: {filepath}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"Erro ao salvar arquivo: {e}", fg=typer.colors.RED)

    # --- LÓGICA DE PLOTAGEM (Inalterada) ---
    if plot:
        plt.figure(figsize=(12, 4))
        color = 'blue' if rhythm == 'fa' else 'red'
        cust_msg = " (Customizado)" if overrides else ""
        title = f"ECG - {'FA' if rhythm == 'fa' else f'Normal ({hr} BPM)'}{cust_msg}"
        
        plt.plot(t, ecg_signal, color=color, linewidth=1.5)
        plt.title(title)
        plt.xlabel("Tempo (segundos)")
        plt.ylabel("Amplitude (z)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    app()