import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
from typing import Optional, Dict

from .constants import ECG_PARAMS_NORMAL, ECG_PARAMS_FA
from .utils import generate_stochastic_f_waves, generate_rr_tachogram
from .derivatives import ecg_derivatives_dynamic
from .noise import add_artifacts

def merge_parameters(base_params: Dict, overrides: Optional[Dict]) -> Dict:
    """Mescla parâmetros base com substituições customizadas."""
    if not overrides:
        return base_params
    
    merged = base_params.copy()
    mapping = {'P': 0, 'Q': 1, 'R': 2, 'S': 3, 'T': 4}
    
    for wave_name, wave_index in mapping.items():
        if wave_name in overrides:
            wave_mods = overrides[wave_name]
            if 'a' in wave_mods:
                merged['a_i'][wave_index] = wave_mods['a']
            if 'b' in wave_mods:
                merged['b_i'][wave_index] = wave_mods['b']
            if 'theta' in wave_mods:
                merged['theta_i'][wave_index] = wave_mods['theta']
                
    return merged

def generate_signal(
    rhythm: str, 
    duration: float, 
    fs: int = 256, 
    hr: float = 60.0,
    hr_std: float = 1.0,
    pqrst_overrides: Optional[Dict] = None,
    # ETAPA 5: Parâmetros de ruído injetados aqui
    bw_amp: float = 0.0,
    pl_amp: float = 0.0,
    noise_std: float = 0.0
):
    """Orquestra a geração do sinal sintético de ECG parametrizável."""
    burn_in = 3.0
    total_duration = duration + burn_in
    t_span = (0, total_duration)
    t_eval = np.linspace(0, total_duration, int(total_duration * fs))
    initial_state = [1.0, 0.0, 0.0]
    
    estimated_beats = int(total_duration * (max(hr, 60.0) / 60.0)) + 15

    if rhythm == "normal":
        rr_intervals = generate_rr_tachogram(estimated_beats, mean_hr=hr, std_hr=hr_std, is_afib=False)
        z0_func = lambda t: 0.0
        base_params = ECG_PARAMS_NORMAL
        
    elif rhythm == "fa":
        fa_std = max(hr_std, 18.0) 
        rr_intervals = generate_rr_tachogram(estimated_beats, mean_hr=hr, std_hr=fa_std, is_afib=True)
        z0_func = generate_stochastic_f_waves(total_duration, fs)
        base_params = ECG_PARAMS_FA
        
    else:
        raise ValueError(f"Ritmo desconhecido: {rhythm}")

    beat_times = np.cumsum(rr_intervals)
    beat_times = np.insert(beat_times, 0, 0.0) 
    omega_values = 2.0 * np.pi / np.insert(rr_intervals, 0, rr_intervals[0])
    omega_func = interp1d(beat_times, omega_values, kind='previous', fill_value="extrapolate")

    final_params = merge_parameters(base_params, pqrst_overrides)

    solution = solve_ivp(
        fun=ecg_derivatives_dynamic,
        t_span=t_span,
        y0=initial_state,
        t_eval=t_eval,
        method='RK45',
        max_step=1.0 / fs, 
        args=(omega_func, final_params, z0_func)
    )
    
    valid_indices = solution.t >= burn_in
    t_final = solution.t[valid_indices] - burn_in
    signal_final = solution.y[2][valid_indices]
    
    # ==========================================
    # ETAPA 5: Pós-processamento e Realismo
    # ==========================================
    
    # 1. Escalonamento Fisiológico
    # Normalizamos o sinal para que o pico mais alto (onda R) seja exatamente 1.0 mV
    # Isso torna as unidades de ruído (--noise 0.03, --pl-amp 0.05) significativas.
    signal_final = signal_final / np.max(np.abs(signal_final))
    
    # 2. Aplicação de Ruídos e Artefatos (Soma linear no sinal escalonado)
    signal_final = add_artifacts(
        t=t_final, 
        signal=signal_final, 
        bw_amp=bw_amp, 
        pl_amp=pl_amp, 
        noise_std=noise_std
    )
    
    return t_final, signal_final