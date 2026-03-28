# packages/cli/src/ecigius_cli/main.py
import typer
import csv
from pathlib import Path
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from typing import Optional

# Importamos o motor matemático do workspace
from ecigius_core import generate_signal
from ecigius_core.validation import ECGValidator

app = typer.Typer(help="Simulador de ECG baseado no modelo de McSharry (CLI)")

@app.command()
def generate(
    # Argumentos Base e Clínicos
    rhythm: str = typer.Option("normal", "--rhythm", "-r", help="Tipo de ritmo: 'normal' ou 'fa'"),
    duration: float = typer.Option(10.0, "--duration", "-d", help="Duração do sinal em segundos"),
    fs: int = typer.Option(256, "--fs", "-f", help="Frequência de amostragem em Hz"),
    hr: float = typer.Option(60.0, "--hr", help="Frequência cardíaca média em BPM"),
    hr_std: float = typer.Option(1.0, "--hr-std", help="Desvio padrão (Variabilidade/Caos) da FC em BPM"),
    
    p_amp: Optional[float] = typer.Option(None, help="Override Amplitude Onda P"),
    p_width: Optional[float] = typer.Option(None, help="Override Largura Onda P"),
    r_amp: Optional[float] = typer.Option(None, help="Override Amplitude Onda R"),
    r_width: Optional[float] = typer.Option(None, help="Override Largura Onda R"),
    
    # Argumentos de Ruido
    bw_amp: float = typer.Option(0.0, "--bw-amp", help="Amplitude do Baseline Wander (Respiração). Ex: 0.15"),
    pl_amp: float = typer.Option(0.0, "--pl-amp", help="Amplitude da Interferência de Rede (60Hz). Ex: 0.05"),
    noise_std: float = typer.Option(0.0, "--noise", help="Desvio Padrão do Ruído Gaussiano. Ex: 0.02"),
    
    plot: bool = typer.Option(True, "--plot/--no-plot", help="Exibe o gráfico após gerar"),
    output: str = typer.Option(None, "--output", "-o", help="Nome do ficheiro (ex: teste.csv)"),
    out_dir: Path = typer.Option(None, "--out-dir", help="Pasta de destino (ex: datasets/)"),

    reference_csv: Path = typer.Option(None, "--reference-csv", help="Caminho para um CSV real do MIT-BIH para validação"),
    val_beats: int = typer.Option(1, "--val-beats", help="Número de batimentos para extrair e alinhar no cálculo do PRD/RMSE") # NOVO PARÂMETRO
    ):
    """
    Gera um sinal sintético de ECG parametrizável e exporta os dados.
    """
    typer.secho(f"Gerando {duration}s de ECG no ritmo '{rhythm.upper()}' a {fs}Hz...", fg=typer.colors.CYAN)
    
    typer.secho(f"Gerando {duration}s de ECG no ritmo '{rhythm.upper()}' a {fs}Hz...", fg=typer.colors.CYAN)
    
    overrides = {}
    if p_amp is not None or p_width is not None:
        overrides['P'] = {'a': p_amp, 'b': p_width} if p_amp and p_width else {'a': p_amp} if p_amp else {'b': p_width}
    if r_amp is not None or r_width is not None:
        overrides['R'] = {'a': r_amp, 'b': r_width} if r_amp and r_width else {'a': r_amp} if r_amp else {'b': r_width}

    try:
        # Passamos as flags de ruído para o gerador
        t, ecg_signal = generate_signal(
            rhythm=rhythm, 
            duration=duration, 
            fs=fs, 
            hr=hr,
            hr_std=hr_std,
            pqrst_overrides=overrides if overrides else None,
            bw_amp=bw_amp,
            pl_amp=pl_amp,
            noise_std=noise_std
        )
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
            typer.secho(f"Erro ao guardar ficheiro: {e}", fg=typer.colors.RED)

    # --- LÓGICA DE PLOTAGEM ---
    if plot:
        plt.figure(figsize=(12, 4))
        color = 'blue' if rhythm == 'fa' else 'red'
        cust_msg = " (Customizado)" if overrides else ""
        title = f"ECG - {'FA' if rhythm == 'fa' else f'Normal'} (FC: {hr} BPM, Var: {hr_std}){cust_msg}"
        
        plt.plot(t, ecg_signal, color=color, linewidth=1.5)
        plt.title(title)
        plt.xlabel("Tempo (segundos)")
        plt.ylabel("Amplitude (z)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    if reference_csv and reference_csv.exists():
        typer.secho(f"\nCarregando template real de: {reference_csv}...", fg=typer.colors.YELLOW)
        try:
            real_data = np.loadtxt(reference_csv, delimiter=',', skiprows=1)
            real_signal = real_data[:, 1]
            
            typer.secho(f"Extraindo e alinhando os {val_beats} primeiros batimentos...", fg=typer.colors.YELLOW)
            # Agora passamos o fs e o num_beats pro validador!
            
            metrics = ECGValidator.validate(ecg_signal, real_signal, fs=fs, num_beats=val_beats)
            
            # --- LÓGICA DOS SELOS INDIVIDUAIS ---
            dtw_val = metrics['dtw_distance']
            prd_val = metrics['prd_percent']
            rmse_val = metrics['rmse']
            
            # Limiares de aceitação
            dtw_ok = "✅" if dtw_val < 0.15 else "❌"
            prd_ok = "✅" if prd_val < 50.0 else "❌"
            rmse_ok = "✅" if rmse_val < 0.30 else "❌" # 0.30 é uma boa margem de erro quadrático
            
            typer.secho("\n--- RELATÓRIO DE VALIDAÇÃO CIENTÍFICA ---", fg=typer.colors.MAGENTA, bold=True)
            typer.echo(f"{dtw_ok} DTW Distance (Macro) : {dtw_val} (Ritmo/Arritmia)")
            typer.echo(f"{prd_ok} PRD Score (Micro)    : {prd_val}% (Morfologia PQRST)")
            typer.echo(f"{rmse_ok} RMSE (Micro)         : {rmse_val}")
            typer.echo(f"   Batimentos Alinhados : {metrics['beats_compared']} de {val_beats} solicitados")
            
            # O Veredito final pode ser "Parcial" se o ritmo estiver correto mas a morfologia não
            if dtw_val < 0.15 and prd_val < 50.0:
                typer.secho("\n🌟 Veredito Geral: SINAL EXCELENTE (Ritmo e Morfologia validados)", fg=typer.colors.GREEN, bold=True)
            elif dtw_val < 0.15:
                typer.secho("\n⚠️ Veredito Geral: RITMO VALIDADO (Ajuste os parâmetros PQRST para melhorar a morfologia)", fg=typer.colors.YELLOW, bold=True)
            else:
                typer.secho("\n❌ Veredito Geral: ALTA DISTORÇÃO (Falha no Ritmo e na Morfologia)", fg=typer.colors.RED, bold=True)
                
            typer.echo("------------------------------------------\n")
            
        except Exception as e:
            typer.secho(f"Erro ao ler referência ou validar: {e}", fg=typer.colors.RED)

if __name__ == "__main__":
    app()