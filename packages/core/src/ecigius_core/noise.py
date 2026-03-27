import numpy as np

def apply_baseline_wander(t: np.ndarray, signal: np.ndarray, freq: float = 0.2, amplitude: float = 0.15) -> np.ndarray:
    """Adiciona oscilação de baixa frequência simulando a respiração do paciente."""
    return signal + amplitude * np.sin(2 * np.pi * freq * t)

def apply_powerline_interference(t: np.ndarray, signal: np.ndarray, freq: float = 60.0, amplitude: float = 0.05) -> np.ndarray:
    """Injeta ruído de rede elétrica (50Hz na Europa/60Hz no Brasil e EUA)."""
    return signal + amplitude * np.sin(2 * np.pi * freq * t)

def apply_gaussian_noise(signal: np.ndarray, std_dev: float = 0.02) -> np.ndarray:
    """Injeta ruído branco gaussiano simulando erro de leitura e ruído térmico do sensor."""
    return signal + np.random.normal(0, std_dev, len(signal))

def add_artifacts(
    t: np.ndarray, 
    signal: np.ndarray, 
    bw_amp: float = 0.0, 
    bw_freq: float = 0.2, 
    pl_amp: float = 0.0, 
    pl_freq: float = 60.0, 
    noise_std: float = 0.0
) -> np.ndarray:
    """Pipeline de pós-processamento que aplica as camadas de ruído sequencialmente."""
    noisy_signal = np.copy(signal)
    
    if bw_amp > 0:
        noisy_signal = apply_baseline_wander(t, noisy_signal, bw_freq, bw_amp)
    if pl_amp > 0:
        noisy_signal = apply_powerline_interference(t, noisy_signal, pl_freq, pl_amp)
    if noise_std > 0:
        noisy_signal = apply_gaussian_noise(noisy_signal, noise_std)
        
    return noisy_signal