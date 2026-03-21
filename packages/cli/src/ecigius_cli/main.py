import typer
import csv
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

# A mágica do Workspace: importamos diretamente do nosso próprio pacote core!
from ecigius_core import generate_signal

app = typer.Typer(help="Simulador de ECG baseado no modelo de McSharry (CLI)")

@app.command()
def generate(
    rhythm: str = typer.Option("fa", "--rhythm", "-r", help="Tipo de ritmo: 'normal' ou 'fa'"),
    duration: float = typer.Option(10.0, "--duration", "-d", help="Duração do sinal em segundos"),
    fs: int = typer.Option(256, "--fs", "-f", help="Frequência de amostragem em Hz"),
    hr: float = typer.Option(60.0, "--hr", help="Frequência cardíaca (apenas ritmo normal)"),
    plot: bool = typer.Option(True, "--plot/--no-plot", help="Exibe o gráfico após gerar"),
    output: str = typer.Option(None, "--output", "-o", help="Nome do arquivo (ex: teste.csv)"),
    out_dir: Path = typer.Option(None, "--out-dir", help="Pasta de destino (ex: datasets/)")
):
    """
    Gera um sinal sintético de ECG e exporta os dados.
    """
    typer.secho(f"Gerando {duration}s de ECG no ritmo '{rhythm.upper()}' a {fs}Hz...", fg=typer.colors.CYAN)
    
    try:
        # A CLI não sabe COMO as equações diferenciais funcionam, ela só chama a função
        t, ecg_signal = generate_signal(rhythm=rhythm, duration=duration, fs=fs, hr=hr)
    except Exception as e:
        typer.secho(f"Erro na geração matemática: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    # --- LÓGICA DE SALVAMENTO ---
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

    # --- LÓGICA DE PLOTAGEM ---
    if plot:
        plt.figure(figsize=(12, 4))
        color = 'blue' if rhythm == 'fa' else 'red'
        title = f"Sinal de ECG - {'Fibrilação Atrial' if rhythm == 'fa' else f'Ritmo Normal ({hr} BPM)'}"
        
        plt.plot(t, ecg_signal, color=color, linewidth=1.5)
        plt.title(title)
        plt.xlabel("Tempo (segundos)")
        plt.ylabel("Amplitude (z)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    app()