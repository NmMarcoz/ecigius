import typer
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
import csv

from pathlib import Path
from datetime import datetime 

# Inicializa o app da CLI
app = typer.Typer(help="Simulador de ECG baseado no modelo de McSharry")

# --- PARÂMETROS MATEMÁTICOS ---
ECG_PARAMS_NORMAL = {
    'theta_i': np.array([-1/3, -1/12, 0, 1/12, 1/2]) * np.pi,
    'a_i': np.array([1.2, -5.0, 30.0, -7.5, 0.75]),
    'b_i': np.array([0.25, 0.1, 0.1, 0.1, 0.4])
}

ECG_PARAMS_FA = ECG_PARAMS_NORMAL.copy()
ECG_PARAMS_FA['a_i'] = np.array([0.0, -5.0, 30.0, -7.5, 0.75]) # Sem onda P

# --- FUNÇÕES CORE ---
def generate_f_waves(t):
    f1, f2, f3 = 4.5, 6.0, 7.5 
    noise = 0.003 * np.sin(2 * np.pi * f1 * t) + \
            0.002 * np.sin(2 * np.pi * f2 * t + 0.8) + \
            0.001 * np.sin(2 * np.pi * f3 * t + 1.5)
    return noise

def generate_afib_rr_intervals(num_beats):
    rr_intervals = []
    for _ in range(num_beats):
        if np.random.rand() < 0.6:
            rr = np.random.normal(0.55, 0.08)
        else:
            rr = np.random.normal(0.85, 0.12)
        rr = np.clip(rr, 0.3, 1.5)
        rr_intervals.append(rr)
    return np.array(rr_intervals)

def ecg_derivatives_dynamic(t, state, omega_func, params, z0_func):
    x, y, z = state
    alpha = 1.0 - np.sqrt(x**2 + y**2)
    omega = omega_func(t) 
    theta = np.arctan2(y, x)
    
    dx_dt = alpha * x - omega * y
    dy_dt = alpha * y + omega * x
    
    dtheta = (theta - params['theta_i']) % (2 * np.pi)
    dtheta[dtheta > np.pi] -= 2 * np.pi
    
    z_sum = np.sum(params['a_i'] * dtheta * np.exp(-0.5 * (dtheta / params['b_i'])**2))
    dz_dt = -z_sum - (z - z0_func(t))
    
    return [dx_dt, dy_dt, dz_dt]

def generate_signal(rhythm: str, duration: float, fs: int, hr: float):
    """Motor unificado para gerar o sinal dependendo do ritmo escolhido."""
    burn_in = 3.0
    total_duration = duration + burn_in
    t_span = (0, total_duration)
    t_eval = np.linspace(0, total_duration, int(total_duration * fs))
    initial_state = [1.0, 0.0, 0.0]
    
    # Configuração das funções de injeção (Dependency Injection matemática)
    if rhythm == "normal":
        omega_const = 2.0 * np.pi * hr / 60.0
        omega_func = lambda t: omega_const
        z0_func = lambda t: 0.0
        params = ECG_PARAMS_NORMAL
    elif rhythm == "fa":
        estimated_beats = int(total_duration * 1.5) + 5
        rr_intervals = generate_afib_rr_intervals(estimated_beats)
        beat_times = np.cumsum(rr_intervals)
        beat_times = np.insert(beat_times, 0, 0.0) 
        omega_values = 2.0 * np.pi / np.insert(rr_intervals, 0, rr_intervals[0])
        omega_func = interp1d(beat_times, omega_values, kind='previous', fill_value="extrapolate")
        z0_func = generate_f_waves
        params = ECG_PARAMS_FA
    else:
        raise ValueError("Ritmo desconhecido.")

    solution = solve_ivp(
        fun=ecg_derivatives_dynamic,
        t_span=t_span,
        y0=initial_state,
        t_eval=t_eval,
        method='RK45',
        args=(omega_func, params, z0_func)
    )
    
    valid_indices = solution.t >= burn_in
    t_final = solution.t[valid_indices] - burn_in
    z_final = solution.y[2][valid_indices]
    
    return t_final, z_final

# --- COMANDOS DA CLI ---
@app.command()
def generate(
    rhythm: str = typer.Option("fa", "--rhythm", "-r", help="Tipo de ritmo: 'normal' ou 'fa'"),
    duration: float = typer.Option(10.0, "--duration", "-d", help="Duração do sinal em segundos"),
    fs: int = typer.Option(256, "--fs", "-f", help="Frequência de amostragem em Hz"),
    hr: float = typer.Option(60.0, "--hr", help="Frequência cardíaca (apenas para ritmo normal)"),
    plot: bool = typer.Option(True, "--plot/--no-plot", help="Exibe o gráfico após gerar"),
    output: str = typer.Option(None, "--output", "-o", help="Nome do arquivo (ex: meu_teste.csv)"),
    out_dir: Path = typer.Option(None, "--out-dir", help="Pasta de destino (ex: datasets/fa_sinais)")
):
    """
    Gera um sinal sintético de ECG (Normal ou Fibrilação Atrial).
    """
    typer.secho(f"Gerando {duration}s de ECG no ritmo '{rhythm.upper()}' a {fs}Hz...", fg=typer.colors.CYAN)
    
    t, ecg_signal = generate_signal(rhythm=rhythm, duration=duration, fs=fs, hr=hr)
    
    # --- LÓGICA DE SALVAMENTO ATUALIZADA ---
    if output or out_dir:
        # Se o usuário não deu um nome de arquivo, geramos um automático
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ecg_{rhythm}_{int(duration)}s_{timestamp}.csv"
        else:
            filename = output

        # Resolvemos o caminho final
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True) # Cria a pasta se não existir
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

    # Plotar, se solicitado
    if plot:
        plt.figure(figsize=(12, 4))
        color = 'blue' if rhythm == 'fa' else 'red'
        title = "Sinal de ECG - Fibrilação Atrial" if rhythm == 'fa' else f"Sinal de ECG - Ritmo Normal ({hr} BPM)"
        
        plt.plot(t, ecg_signal, color=color, linewidth=1.5)
        plt.title(title)
        plt.xlabel("Tempo (segundos)")
        plt.ylabel("Amplitude (z)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    app()