# fetch_mitbih.py
import wfdb
import numpy as np
import csv

def fetch_and_save_record(
    record_name: str = '201', 
    db_name: str = 'mitdb', 
    output_file: str = './files/template_mitbih_201_fa.csv', 
    duration_sec: int = 10
):
    """
    Baixa um registro real do MIT-BIH Arrhythmia Database e salva como CSV.
    O registro '201' é um caso clássico que contém episódios de Fibrilação Atrial.
    """
    print(f"📥 Baixando o registro '{record_name}' do banco '{db_name}' via PhysioNet...")
    
    try:
        # A mágica do wfdb: se ele não achar local, ele baixa via API da PhysioNet
        record = wfdb.rdrecord(record_name, pn_dir=db_name)
        
        fs_original = record.fs
        print(f"📊 Dados carregados! Frequência de amostragem real: {fs_original} Hz")
        
        # O banco MIT-BIH tem 2 derivações por paciente.
        # A coluna 0 geralmente é a MLII (Modificada derivação II), que tem a onda R bem visível.
        sig_name = record.sig_name[0]
        print(f"🫀 Extraindo a derivação: {sig_name}")
        
        num_samples = int(duration_sec * fs_original)
        signal = record.p_signal[:num_samples, 0]
        
        # Gerar o eixo do tempo
        time = np.arange(num_samples) / fs_original
        
        # Salvar no nosso formato padrão CSV
        with open(output_file, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'amplitude'])
            for t_val, amp_val in zip(time, signal):
                writer.writerow([f"{t_val:.4f}", f"{amp_val:.4f}"])
                
        print(f"✅ Sucesso! Template salvo em: {output_file}")
        
    except Exception as e:
        print(f"❌ Erro ao baixar ou processar os dados: {e}")

if __name__ == '__main__':
    # Vamos baixar 10 segundos do paciente 201 para bater com os nossos 10s gerados
    fetch_and_save_record(duration_sec=10)