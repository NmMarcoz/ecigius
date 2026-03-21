import numpy as np
import matplotlib.pyplot as plt
from generate_ecg import generate_ecg

def plot_ecg(t, z_signal):
    """Plota o sinal gerado para validação visual."""
    plt.figure(figsize=(12, 4))
    plt.plot(t, z_signal, color='red', linewidth=1.5)
    plt.title("Sinal de ECG Sintético (Modelo de McSharry)")
    plt.xlabel("Tempo (segundos)")
    plt.ylabel("Amplitude (z)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    return

if __name__ == "__main__":
    print("Gerando 10 segundos de ECG a 60 BPM...")
    t, ecg_signal = generate_ecg(duration=10.0, fs=256, hr=60.0)
    plot_ecg(t, ecg_signal)
    print("done!")
    