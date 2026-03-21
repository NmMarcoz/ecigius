from ecg_derivatives import ecg_derivatives
from scipy.integrate import solve_ivp
import numpy as np

def generate_ecg(duration=10.0, fs=256, hr=60.0):
    burn_in = 3.0 # Segundos de "aquecimento" para estabilizar as EDOs
    total_duration = duration + burn_in
    
    t_span = (0, total_duration)
    t_eval = np.linspace(0, total_duration, int(total_duration * fs))
    initial_state = [1.0, 0.0, 0.0]
    
    # ... (código do solve_ivp continua igual) ...
    solution = solve_ivp(
        fun=ecg_derivatives,
        t_span=t_span,
        y0=initial_state,
        t_eval=t_eval,
        method='RK45',
        args=(hr, 0.0)
    )
    
    # Filtra o período transiente
    valid_indices = solution.t >= burn_in
    t_final = solution.t[valid_indices] - burn_in # Reinicia o tempo do zero
    z_final = solution.y[2][valid_indices]
    
    return t_final, z_final