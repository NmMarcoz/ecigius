# packages/core/src/ecigius_core/generator.py
import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
from typing import Optional, Dict, List

from .constants import ECG_PARAMS_NORMAL, ECG_PARAMS_FA
from .utils import generate_f_waves, generate_afib_rr_intervals
from .derivatives import ecg_derivatives_dynamic

def merge_parameters(base_params: Dict, overrides: Optional[Dict]) -> Dict:
    """Mescla parâmetros base com substituições customizadas."""
    if not overrides:
        return base_params
    
    merged = base_params.copy()
    # Índices: P=0, Q=1, R=2, S=3, T=4
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
    pqrst_overrides: Optional[Dict] = None # Nova opção para customização morfológica
):
    """Orquestra a geração do sinal sintético de ECG parametrizável."""
    burn_in = 3.0
    total_duration = duration + burn_in
    t_span = (0, total_duration)
    t_eval = np.linspace(0, total_duration, int(total_duration * fs))
    initial_state = [1.0, 0.0, 0.0]
    
    # Seleção base do ritmo
    if rhythm == "normal":
        omega_func = lambda t: 2.0 * np.pi * hr / 60.0
        z0_func = lambda t: 0.0
        base_params = ECG_PARAMS_NORMAL
        
    elif rhythm == "fa":
        estimated_beats = int(total_duration * 1.5) + 5
        rr_intervals = generate_afib_rr_intervals(estimated_beats)
        beat_times = np.cumsum(rr_intervals)
        beat_times = np.insert(beat_times, 0, 0.0) 
        omega_values = 2.0 * np.pi / np.insert(rr_intervals, 0, rr_intervals[0])
        omega_func = interp1d(beat_times, omega_values, kind='previous', fill_value="extrapolate")
        z0_func = generate_f_waves
        base_params = ECG_PARAMS_FA
        
    else:
        raise ValueError(f"Ritmo desconhecido: {rhythm}")

    # Aplica parametrização customizada da Etapa 2
    final_params = merge_parameters(base_params, pqrst_overrides)

    solution = solve_ivp(
        fun=ecg_derivatives_dynamic,
        t_span=t_span,
        y0=initial_state,
        t_eval=t_eval,
        method='RK45',
        args=(omega_func, final_params, z0_func)
    )
    
    valid_indices = solution.t >= burn_in
    return solution.t[valid_indices] - burn_in, solution.y[2][valid_indices]