import numpy as np

# Parâmetros Base (Ritmo Sinusal Normal)
ECG_PARAMS_NORMAL = {
    'theta_i': np.array([-1/3, -1/12, 0, 1/12, 1/2]) * np.pi,
    'a_i': np.array([1.2, -5.0, 30.0, -7.5, 0.75]),
    'b_i': np.array([0.25, 0.1, 0.1, 0.1, 0.4])
}

# Parâmetros para Fibrilação Atrial (Sem Onda P)
ECG_PARAMS_FA = ECG_PARAMS_NORMAL.copy()
ECG_PARAMS_FA['a_i'] = np.array([0.0, -5.0, 30.0, -7.5, 0.75])