# Ecigius: Synthetic ECG Simulator

**Ecigius** is a ecg generator based on the **McSharry model**. It uses a system of thridimensional ordinary differential equations to model the P-Q-R-S-T morphology.

Besides the sinus normal rhytm, the matematic motor has native support to **Atrial Fibrilation (AF)** simulation.

## Architecture

It's an uv monorepo.

The workspace is separated in three principal packages:
 - **`ecigius-core`**: the mathemmatic motor. Has the equations and constants used in the **McSharry** model. It uses `numpy` and `scipy`.

 - **`ecigius-cli`**: The ecigius cli. It uses `Typer`, and can export to csv the generated ecgs.

 - **`ecigius-tui`**: The ecigius terminal interface. Built with `Textual`.

----

## Installing
Requisits:
- Python (>=3.10) 
- [uv](https://github.com/astral-sh/uv)

Steps:
1. Clone the repository
2. In the root, install the dependencies and sync with uv:

```bash
uv sync
```

Isso criará um único ambiente virtual (.venv) na raiz com todos os pacotes perfeitamente linkados.
🛠️ Como Usar

----

## Usage
At this moment, you can use in two ways:
- The CLI
- The TUI

Pick the one you like most, or build yourself a interface for this.


### 1. CLI Usage


#### Help 

```bash
uv run ecg-cli --help
```

#### Plotting a 10 seconds ecg and saving to a .csv

```bash
uv run ecg-cli --rhythm fa --duration 10 --out-dir datasets/
```

#### Generating a 30 seconds ecg without plotting.
```bash
uv run ecg-cli --rhythm normal --hr 80 --duration 30 --no-plot --output teste_normal.csv
```

### 2. TUI Usage

Just run the TUI in the terminal:

```bash
uv run ecg-tui
```

---

## Mathematical Model (McSharry)

The generator utilizate the following system to produce the signal on z axis:


$$\dot{x} = \alpha x - \omega y$$

$$\dot{y} = \alpha y + \omega x$$

$$\dot{z} = -\sum_{i \in \{P,Q,R,S,T\}} a_i \Delta\theta_i \exp\left(-\frac{\Delta\theta_i^2}{2b_i^2}\right) - (z - z_0)$$

Where:

    α: Is defined as 1−x2+y2​, which forces the trajectory to return to the limit cycle (a circle of unit radius) if it deviates.

    ω: Is the angular velocity, which controls the heart rate (RR interval).

    Δθi​: Is the angular difference (θ−θi​)(mod2π), where θ=atan2(y,x) is the current angle of the trajectory.

    ai​,bi​,θi​: Represent the amplitude, width, and phase (angular position) of each of the five corresponding ECG waves (P, Q, R, S, T), respectively.

    z0​: Represents the baseline wander term, which can be coupled to respiratory frequency or used to inject fibrillatory noise (f-waves).

---

## Roadmap

    [x] Motor Matemático Base (Modelo de McSharry).

    [x] Suporte para Fibrilação Atrial (Ondas f, Sem P, RR Irregular).

    [x] Exportação para CSV.

    [x] Arquitetura de pacotes separada (Core, CLI, TUI).

    [ ] Injeção de ruído EMG (Artefato de Movimento Muscular).

    [ ] Interface Gráfica Desktop (UI).
