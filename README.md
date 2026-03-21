# 🫀 Ecigius: Simulador de Sinais Sintéticos de ECG

**Ecigius** é um gerador de sinais de eletrocardiograma (ECG) sintéticos baseado no renomado **Modelo Matemático de McSharry et al.** Ele utiliza um sistema de equações diferenciais ordinárias (EDOs) tridimensionais para modelar com alta precisão a morfologia P-Q-R-S-T.

Além do ritmo sinusal normal, o motor matemático possui suporte nativo para simulação de **Fibrilação Atrial (FA)**, implementando a ausência da onda P, variabilidade caótica do intervalo RR e injeção de ruído fibrilatório (ondas *f*) na linha de base.

## 🏗️ Arquitetura do Projeto

O projeto é um **monorepo** gerenciado pelo `uv`, separado por packages.

O workspace é dividido em três pacotes principais:

* 🧠 **`ecigius-core`**: O motor matemático. Contém as EDOs, constantes do modelo de McSharry e integrações numéricas numéricas usando `numpy` e `scipy.integrate`.
* 💻 **`ecigius-cli`**: Uma CLI rápida e tipada construída com `Typer`. Permite gerar sinais em lote, visualizar via `matplotlib` e exportar datasets para `.csv`.
* 📟 **`ecigius-tui`**: Uma TUI interativa construída com `Textual`. Inclui plotagem nativa do sinal diretamente no terminal usando caracteres Braille (`plotext`).

## 🚀 Instalação e Configuração

Pré-requisitos: 
- Python (>=3.10) 
- [uv](https://github.com/astral-sh/uv)

1. Clone o repositório.
2. Na raiz do projeto, instale as dependências e faça o link do workspace:
```bash
uv sync
```
