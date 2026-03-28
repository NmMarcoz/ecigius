# packages/core/src/ecigius_core/validation.py
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from scipy.signal import find_peaks

class ECGValidator:
    """Módulo de validação estatística e morfológica para sinais de ECG."""
    
    @staticmethod
    def extract_beats(signal: np.ndarray, fs: int, num_beats: int = 1) -> list:
        """
        Encontra os picos R e recorta uma janela exata em torno de cada batimento.
        Janela padrão clínica: 250ms antes do R, 400ms depois do R.
        """
        # Distância mínima entre picos (ex: 0.4s = 150 BPM máx) para evitar falsos positivos
        min_dist = int(fs * 0.4) 
        # Altura mínima (dinâmica baseada no sinal)
        min_height = np.max(signal) * 0.5 
        
        peaks, _ = find_peaks(signal, distance=min_dist, height=min_height)
        
        # Define as margens da janela em amostras
        left_margin = int(0.25 * fs)
        right_margin = int(0.40 * fs)
        
        beats = []
        for p in peaks:
            if len(beats) >= num_beats:
                break
            # Ignora picos muito colados nas bordas do sinal
            if p - left_margin >= 0 and p + right_margin < len(signal):
                beat_window = signal[p - left_margin : p + right_margin]
                beats.append(beat_window)
                
        return beats

    @staticmethod
    def align_and_truncate(sig1: np.ndarray, sig2: np.ndarray):
        min_len = min(len(sig1), len(sig2))
        return sig1[:min_len], sig2[:min_len]

    @staticmethod
    def calculate_rmse(synthetic: np.ndarray, real: np.ndarray) -> float:
        s_syn, s_real = ECGValidator.align_and_truncate(synthetic, real)
        return np.sqrt(np.mean((s_syn - s_real) ** 2))

    @staticmethod
    def calculate_prd(synthetic: np.ndarray, real: np.ndarray) -> float:
        s_syn, s_real = ECGValidator.align_and_truncate(synthetic, real)
        
        s_syn = s_syn - np.mean(s_syn)
        s_real = s_real - np.mean(s_real)
        
        if np.max(np.abs(s_syn)) > 0:
            s_syn = s_syn / np.max(np.abs(s_syn))
        if np.max(np.abs(s_real)) > 0:
            s_real = s_real / np.max(np.abs(s_real))
            
        # --- A MÁGICA ENTRA AQUI ---
        # Desliza o sinal sintético para "acoplar" perfeitamente no sinal real
        correlation = np.correlate(s_real, s_syn, mode='full')
        best_shift = np.argmax(correlation) - (len(s_syn) - 1)
        s_syn = np.roll(s_syn, best_shift)
        # ---------------------------
            
        numerator = np.sum((s_real - s_syn) ** 2)
        denominator = np.sum(s_real ** 2)
        
        if denominator == 0:
            return float('inf')
            
        return np.sqrt(numerator / denominator) * 100.0

    @staticmethod
    def calculate_dtw(synthetic: np.ndarray, real: np.ndarray) -> float:
        step = 4 
        s_syn_downsampled = synthetic[::step].reshape(-1, 1)
        s_real_downsampled = real[::step].reshape(-1, 1)
        
        distance, path = fastdtw(s_syn_downsampled, s_real_downsampled, dist=euclidean)
        return distance / len(path)

    @classmethod
    def validate(cls, synthetic: np.ndarray, real: np.ndarray, fs: int = 256, num_beats: int = 1) -> dict:
        """Roda a suíte completa de validação macro (Ritmo) e micro (Batimento)."""
        synthetic = np.asarray(synthetic).flatten()
        real = np.asarray(real).flatten()
        
        norm_syn = synthetic / (np.max(np.abs(synthetic)) or 1)
        norm_real = real / (np.max(np.abs(real)) or 1)
        
        # 1. Validação Macro (Sinal Completo - Foco no Ritmo e Arritmia)
        dtw_dist = cls.calculate_dtw(norm_syn, norm_real)
        
        # 2. Validação Micro (Morfologia PQRST focada em 'N' batimentos alinhados)
        syn_beats = cls.extract_beats(norm_syn, fs, num_beats)
        real_beats = cls.extract_beats(norm_real, fs, num_beats)
        
        prd_scores = []
        rmse_scores = []
        
        # Compara par a par os batimentos encontrados
        pairs_to_compare = min(len(syn_beats), len(real_beats))
        for i in range(pairs_to_compare):
            prd_scores.append(cls.calculate_prd(syn_beats[i], real_beats[i]))
            rmse_scores.append(cls.calculate_rmse(syn_beats[i], real_beats[i]))
            
        # Tira a média dos scores dos batimentos (ou usa 100% se falhou em extrair)
        final_prd = np.mean(prd_scores) if prd_scores else 100.0
        final_rmse = np.mean(rmse_scores) if rmse_scores else 1.0
        
        is_acceptable = dtw_dist < 0.15 and final_prd < 50.0
        
        return {
            "dtw_distance": round(dtw_dist, 4),
            "prd_percent": round(final_prd, 2),
            "rmse": round(final_rmse, 4),
            "beats_compared": pairs_to_compare,
            "clinically_acceptable": is_acceptable
        }