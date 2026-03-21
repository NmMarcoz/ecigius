import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d

from .constants import ECG_PARAMS_NORMAL, ECG_PARAMS_FA
from .utils import generate_f_waves, generate_afib_rr_intervals
from .derivatives import ecg_derivatives_dynamic

def generate_signal(rhythm: str, duration: float, fs: int = 256, hr: float = 60.0):
    """Orquestra a geração do sinal sintético de ECG."""
    burn_in = 3.0
    total_duration = duration + burn_in
    t_span = (0, total_duration)
    t_eval = np.linspace(0, total_duration, int(total_duration * fs))
    initial_state = [1.0, 0.0, 0.0]
    
    if rhythm == "normal":
        omega_func = lambda t: 2.0 * np.pi * hr / 60.0
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
        raise ValueError(f"Ritmo desconhecido: {rhythm}")

    solution = solve_ivp(
        fun=ecg_derivatives_dynamic,
        t_span=t_span,
        y0=initial_state,
        t_eval=t_eval,
        method='RK45',
        args=(omega_func, params, z0_func)
    )
    
    valid_indices = solution.t >= burn_in
    return solution.t[valid_indices] - burn_in, solution.y[2][valid_indices]