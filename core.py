# core.py
import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d

ECG_PARAMS_NORMAL = {
    'theta_i': np.array([-1/3, -1/12, 0, 1/12, 1/2]) * np.pi,
    'a_i': np.array([1.2, -5.0, 30.0, -7.5, 0.75]),
    'b_i': np.array([0.25, 0.1, 0.1, 0.1, 0.4])
}

ECG_PARAMS_FA = ECG_PARAMS_NORMAL.copy()
ECG_PARAMS_FA['a_i'] = np.array([0.0, -5.0, 30.0, -7.5, 0.75])

def generate_f_waves(t):
    f1, f2, f3 = 4.5, 6.0, 7.5 
    return 0.003 * np.sin(2 * np.pi * f1 * t) + \
           0.002 * np.sin(2 * np.pi * f2 * t + 0.8) + \
           0.001 * np.sin(2 * np.pi * f3 * t + 1.5)

def generate_afib_rr_intervals(num_beats):
    rr_intervals = []
    for _ in range(num_beats):
        rr = np.random.normal(0.55, 0.08) if np.random.rand() < 0.6 else np.random.normal(0.85, 0.12)
        rr_intervals.append(np.clip(rr, 0.3, 1.5))
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
        raise ValueError("Ritmo desconhecido.")

    solution = solve_ivp(
        fun=ecg_derivatives_dynamic, t_span=t_span, y0=initial_state,
        t_eval=t_eval, method='RK45', args=(omega_func, params, z0_func)
    )
    
    valid_indices = solution.t >= burn_in
    return solution.t[valid_indices] - burn_in, solution.y[2][valid_indices]