import numpy as np
from scipy.interpolate import interp1d

def generate_stochastic_f_waves(total_duration: float, fs: int = 256) -> callable:
    """
    Gera ruído fibrilatório (ondas f) estocástico realista na banda de 3Hz a 12Hz.
    Retorna uma função interpolada z0(t) pronta para ser consumida pela EDO.
    """
    n_samples = int(total_duration * fs)
    t = np.linspace(0, total_duration, n_samples)
    
    # 1. Criação do eixo de frequências
    freqs = np.fft.rfftfreq(n_samples, d=1.0/fs)
    
    # 2. Construção do Espectro de Potência S(f) para a FA
    # Ondas f reais têm um pico de potência dominante em torno de 6 Hz
    S = np.zeros_like(freqs)
    f_peak = 6.0 
    
    # Cria uma curva Gaussiana focada no pico de 6Hz
    S = np.exp(-0.5 * ((freqs - f_peak) / 1.5)**2) 
    
    # Zera as frequências fora da banda fibrilatória clínica (3 a 12 Hz)
    S[(freqs < 3.0) | (freqs > 12.0)] = 0.0
    
    # 3. Injeção de fases aleatórias para criar o caos
    phases = 2 * np.pi * np.random.rand(len(S))
    complex_spectrum = np.sqrt(S) * np.exp(1j * phases)
    
    # 4. IFFT para voltar ao domínio do tempo
    f_waves = np.fft.irfft(complex_spectrum, n=n_samples)
    
    # 5. Normalização e Escalonamento da amplitude na coordenada z
    # 0.015 é um bom valor empírico para a amplitude das ondas f no modelo
    f_waves = (f_waves / np.std(f_waves)) * 0.015 
    
    # Retorna a função interpolada. Isso é MUITO mais rápido para o solve_ivp 
    # do que calcular senoides a cada micro-passo de integração.
    return interp1d(t, f_waves, kind='cubic', fill_value="extrapolate")

def generate_f_waves(t):
    """Gera ruído contínuo de ondas 'f' para a linha de base."""
    f1, f2, f3 = 4.5, 6.0, 7.5 
    noise = 0.003 * np.sin(2 * np.pi * f1 * t) + \
            0.002 * np.sin(2 * np.pi * f2 * t + 0.8) + \
            0.001 * np.sin(2 * np.pi * f3 * t + 1.5)
    return noise

def generate_rr_tachogram(num_beats: int, mean_hr: float = 60.0, std_hr: float = 1.0, is_afib: bool = False) -> np.ndarray:
    """
    Gera o tacograma RR usando o método espectral (IFFT) de McSharry.
    Converte uma densidade espectral de potência (PSD) em uma série temporal.
    """
    # Parâmetros base do espectro (Frequência e Largura dos picos LF e HF)
    f1, f2 = 0.1, 0.25
    c1, c2 = 0.01, 0.01
    lf_hf_ratio = 0.5

    if is_afib:
        # Na FA, o espectro perde os picos definidos e vira um ruído caótico de banda larga
        c1, c2 = 0.2, 0.2 
        std_hr = max(std_hr, 15.0) # Força alta variabilidade (ex: desvio de 15+ bpm)
        lf_hf_ratio = 1.0

    # Criação do eixo de frequências
    f = np.linspace(0, 0.5, num_beats // 2 + 1)
    
    # Construção do Espectro de Potência S(f)
    S = np.zeros_like(f)
    # Evita divisão por zero no índice 0
    S[1:] = (lf_hf_ratio**2 / np.sqrt(2 * np.pi * c1**2)) * np.exp(-0.5 * ((f[1:] - f1) / c1)**2) + \
            (1.0 / np.sqrt(2 * np.pi * c2**2)) * np.exp(-0.5 * ((f[1:] - f2) / c2)**2)

    # Injeção de fases aleatórias para garantir estocasticidade
    phases = 2 * np.pi * np.random.rand(len(S))
    complex_spectrum = np.sqrt(S) * np.exp(1j * phases)

    # Transformada Rápida de Fourier Inversa (IFFT) para o domínio do tempo
    rr_fluctuations = np.fft.irfft(complex_spectrum, n=num_beats)

    # Normalização (Z-score) para controlar a média e desvio padrão finais
    rr_fluctuations = (rr_fluctuations - np.mean(rr_fluctuations)) / np.std(rr_fluctuations)

    # Conversão de BPM para Segundos (Intervalo RR)
    mean_rr = 60.0 / mean_hr
    std_rr = (60.0 / (mean_hr**2)) * std_hr # Aproximação de Taylor para a variância do RR

    # Aplica a média e o desvio à série normalizada
    tachogram = mean_rr + (rr_fluctuations * std_rr)

    # Clipa em valores fisiológicos extremos para o integrador (EDO) não explodir
    tachogram = np.clip(tachogram, 0.25, 2.0)

    return tachogram