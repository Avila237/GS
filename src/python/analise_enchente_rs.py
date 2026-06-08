"""analise_enchente_rs.py — Análise exploratória da enchente do RS (2024).

Carrega os CSVs limpos por ``data_loader.py``, recorta a janela da enchente
(abril–maio/2024, sem descartar o restante) e gera três figuras PNG:

1. Nível do rio (estação 71350001) vs tempo, com cotas de alerta e inundação;
2. Precipitação acumulada diária (estação 2650035);
3. Scatter precipitação acumulada 24h × nível do rio (correlação).

Também imprime estatísticas descritivas básicas do período.

Uso:
    python analise_enchente_rs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend headless: salva PNG sem display
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Importa metadados/caminhos do loader irmão (reaproveita as estações).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_loader as dl  # noqa: E402

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #
FIGURES_DIR = dl.REPO_ROOT / "outputs" / "figuras"

# Janela da enchente (filtro, não descarte). Limites inclusivos.
PERIOD_START = "2024-04-01"
PERIOD_END = "2024-05-31 23:00:00"

# Estações de interesse.
RIVER_MAIN = "71350001"  # rio principal, quase completo
RAIN_MAIN = "2650035"  # pluviômetro principal

# Cotas de referência (cm) — ILUSTRATIVAS. Substituir pelas cotas oficiais
# de alerta/inundação da estação no ANA HidroWeb antes de uso operacional.
ALERTA_CM = 500.0
INUNDACAO_CM = 600.0

_STATION_BY_CODE = {s.code: s for s in dl.STATIONS}


# --------------------------------------------------------------------------- #
# Carga e recorte
# --------------------------------------------------------------------------- #
def load_processed(processed_dir: str | Path = dl.PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Carrega os CSVs processados em um dict ``{codigo: DataFrame}``."""
    processed_dir = Path(processed_dir)
    frames: dict[str, pd.DataFrame] = {}
    for station in dl.STATIONS:
        path = processed_dir / f"{station.kind}_{station.code}.csv"
        frames[station.code] = pd.read_csv(path, parse_dates=["datetime"])
    return frames


def filter_period(
    df: pd.DataFrame, start: str = PERIOD_START, end: str = PERIOD_END
) -> pd.DataFrame:
    """Recorta o DataFrame ao intervalo ``[start, end]`` (não muta a entrada)."""
    mask = (df["datetime"] >= start) & (df["datetime"] <= end)
    return df.loc[mask].copy()


# --------------------------------------------------------------------------- #
# Cálculos
# --------------------------------------------------------------------------- #
def daily_accumulated(df: pd.DataFrame, value_col: str) -> pd.Series:
    """Soma diária do valor (ex.: precipitação acumulada por dia)."""
    series = df.set_index("datetime")[value_col]
    # min_count=1: dia totalmente ausente vira NaN em vez de 0.
    return series.resample("D").sum(min_count=1)


def rolling_accumulated(
    df: pd.DataFrame, value_col: str, window: str = "24h", min_periods: int = 20
) -> pd.Series:
    """Soma móvel no tempo (ex.: precipitação acumulada nas últimas 24h)."""
    series = df.set_index("datetime")[value_col].sort_index()
    return series.rolling(window, min_periods=min_periods).sum()


def build_correlation_frame(
    precip_df: pd.DataFrame, nivel_df: pd.DataFrame
) -> pd.DataFrame:
    """Alinha precipitação acumulada 24h e nível do rio no mesmo timestamp."""
    precip_24h = rolling_accumulated(precip_df, "precipitacao_mm")
    precip_24h.name = "precip_24h_mm"
    nivel = nivel_df.set_index("datetime")["nivel_cm"]
    merged = pd.concat([precip_24h, nivel], axis=1, join="inner").dropna()
    return merged


def describe_period(frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Estatísticas básicas (min/máx/média/n/ausentes) por estação na janela."""
    stats: dict[str, dict] = {}
    for code, df in frames.items():
        value_col = _STATION_BY_CODE[code].value_column
        window = filter_period(df)
        col = window[value_col]
        stats[code] = {
            "value_col": value_col,
            "n": int(len(col)),
            "ausentes": int(col.isna().sum()),
            "min": float(col.min()) if col.notna().any() else float("nan"),
            "max": float(col.max()) if col.notna().any() else float("nan"),
            "media": float(col.mean()) if col.notna().any() else float("nan"),
        }
    return stats


def print_stats(stats: dict[str, dict]) -> None:
    """Imprime a tabela de estatísticas descritivas do período."""
    print(f"\nEstatísticas descritivas — {PERIOD_START} a {PERIOD_END}")
    print(f"{'estação':>10} {'coluna':>16} {'n':>6} {'ausent':>7} "
          f"{'min':>9} {'máx':>9} {'média':>9}")
    for code, s in stats.items():
        print(f"{code:>10} {s['value_col']:>16} {s['n']:>6} {s['ausentes']:>7} "
              f"{s['min']:>9.2f} {s['max']:>9.2f} {s['media']:>9.2f}")


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def plot_river_level(
    nivel_window: pd.DataFrame,
    out_path: str | Path,
    alerta_cm: float = ALERTA_CM,
    inundacao_cm: float = INUNDACAO_CM,
) -> Path:
    """Gráfico 1: nível do rio vs tempo com cotas de alerta e inundação."""
    out_path = Path(out_path)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(nivel_window["datetime"], nivel_window["nivel_cm"],
            color="#1f77b4", lw=1.2, label=f"Nível {RIVER_MAIN}")
    ax.axhline(alerta_cm, color="orange", ls="--", lw=1.5,
               label=f"Alerta ({alerta_cm:.0f} cm)*")
    ax.axhline(inundacao_cm, color="red", ls="--", lw=1.5,
               label=f"Inundação ({inundacao_cm:.0f} cm)*")
    ax.set_title(f"Nível do rio — estação {RIVER_MAIN} (abr–mai/2024)")
    ax.set_xlabel("Data")
    ax.set_ylabel("Nível (cm)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")
    fig.text(0.01, 0.01, "* cotas ilustrativas — confirmar no ANA HidroWeb",
             fontsize=7, color="gray")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_daily_precip(daily: pd.Series, out_path: str | Path) -> Path:
    """Gráfico 2: precipitação acumulada diária."""
    out_path = Path(out_path)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(daily.index, daily.values, width=0.8, color="#2c7fb8")
    ax.set_title(f"Precipitação acumulada diária — estação {RAIN_MAIN} (abr–mai/2024)")
    ax.set_xlabel("Data")
    ax.set_ylabel("Precipitação (mm/dia)")
    ax.grid(alpha=0.3, axis="y")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_precip_vs_level(merged: pd.DataFrame, out_path: str | Path) -> Path:
    """Gráfico 3: scatter precipitação acumulada 24h × nível do rio."""
    out_path = Path(out_path)
    corr = merged["precip_24h_mm"].corr(merged["nivel_cm"])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(merged["precip_24h_mm"], merged["nivel_cm"],
               s=10, alpha=0.4, color="#238b45")
    ax.set_title("Precipitação acumulada 24h × nível do rio (abr–mai/2024)\n"
                 f"Pearson r = {corr:.2f}")
    ax.set_xlabel(f"Precipitação acumulada 24h — {RAIN_MAIN} (mm)")
    ax.set_ylabel(f"Nível do rio — {RIVER_MAIN} (cm)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
def main(
    processed_dir: str | Path = dl.PROCESSED_DIR,
    figures_dir: str | Path = FIGURES_DIR,
) -> list[Path]:
    """Pipeline completo: carrega, recorta, plota e imprime estatísticas."""
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    frames = load_processed(processed_dir)

    nivel_window = filter_period(frames[RIVER_MAIN])
    precip_window = filter_period(frames[RAIN_MAIN])

    daily = daily_accumulated(precip_window, "precipitacao_mm")
    merged = build_correlation_frame(precip_window, nivel_window)

    outputs = [
        plot_river_level(nivel_window, figures_dir / "g1_nivel_71350001_abr_mai_2024.png"),
        plot_daily_precip(daily, figures_dir / "g2_precip_diaria_2650035_abr_mai_2024.png"),
        plot_precip_vs_level(merged, figures_dir / "g3_scatter_precip24h_vs_nivel.png"),
    ]

    print_stats(describe_period(frames))
    print(f"\nFiguras salvas em: {figures_dir}")
    for p in outputs:
        print(f"  - {p.name}")
    return outputs


if __name__ == "__main__":
    # Console Windows (cp1252) pode falhar com acentos; força UTF-8 se possível.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
