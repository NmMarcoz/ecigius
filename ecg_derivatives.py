import numpy as np


# 1. Dicionário de Parâmetros (Baseado na Tabela I do McSharry)
# Índices: P, Q, R, S, T
ECG_PARAMS = {
    'theta_i': np.array([-1/3, -1/12, 0, 1/12, 1/2]) * np.pi,
    'a_i': np.array([1.2, -5.0, 30.0, -7.5, 0.75]),
    'b_i': np.array([0.25, 0.1, 0.1, 0.1, 0.4])
}

def ecg_derivatives(t, state, hr=60.0, z0=0.0):
    """
    Sistema de equações diferenciais para a trajetória 3D do ECG.
    
    t: tempo atual (usado pelo solver)
    state: lista ou array com [x, y, z]
    hr: Frequência cardíaca em batimentos por minuto (BPM)
    z0: Deslocamento da linha de base (Baseline wander)
    """
    x, y, z = state
    
    # Cálculos base
    alpha = 1.0 - np.sqrt(x**2 + y**2)
    omega = 2.0 * np.pi * hr / 60.0 # Velocidade angular (rad/s)
    
    # Ângulo atual no plano x,y
    theta = np.arctan2(y, x)
    
    # Equações para x e y (Ciclo Limite)
    dx_dt = alpha * x - omega * y
    dy_dt = alpha * y + omega * x
    
    # Cálculo da diferença angular (fase) com wrapping para o intervalo [-pi, pi]
    dtheta = (theta - ECG_PARAMS['theta_i']) % (2 * np.pi)
    dtheta[dtheta > np.pi] -= 2 * np.pi
    
    # Equação para z (Morfologia P-Q-R-S-T)
    # A soma de todas as gaussianas das ondas
    z_sum = np.sum(ECG_PARAMS['a_i'] * dtheta * np.exp(-0.5 * (dtheta / ECG_PARAMS['b_i'])**2))
    dz_dt = -z_sum - (z - z0)
    
    return [dx_dt, dy_dt, dz_dt]