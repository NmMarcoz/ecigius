import numpy as np

def generate_f_waves(t):
    """Gera ruído contínuo de ondas 'f' para a linha de base."""
    f1, f2, f3 = 4.5, 6.0, 7.5 
    noise = 0.003 * np.sin(2 * np.pi * f1 * t) + \
            0.002 * np.sin(2 * np.pi * f2 * t + 0.8) + \
            0.001 * np.sin(2 * np.pi * f3 * t + 1.5)
    return noise

def generate_afib_rr_intervals(num_beats):
    """Gera uma sequência de intervalos RR bimodal (caótica)."""
    rr_intervals = []
    for _ in range(num_beats):
        if np.random.rand() < 0.6:
            rr = np.random.normal(0.55, 0.08)
        else:
            rr = np.random.normal(0.85, 0.12)
        rr = np.clip(rr, 0.3, 1.5)
        rr_intervals.append(rr)
    return np.array(rr_intervals)