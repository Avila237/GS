"""grafico_disponibilidade.py — Disponibilidade dos pluviômetros (abr–mai/2024).

Argumento central do projeto: durante a enchente do RS de 2024 a própria
infraestrutura de monitoramento colapsa. Este script torna esse colapso
visível — uma estação (2650035) segue quase 100% operante enquanto a outra
(83967) fica 100% muda em todo o período crítico.

Carrega os dois CSVs de precipitação limpos por ``data_loader.py``, recorta a
janela abril–maio/2024 e gera uma única figura PNG: duas faixas temporais lado
a lado (empilhadas), verde onde há leitura e vermelho onde o dado é ``NaN``.

Uso:
    python grafico_disponibilidade.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend headless: salva PNG sem display
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Reaproveita caminhos/metadados do loader e o recorte de período da análise.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analise_enchente_rs as ar  # noqa: E402  (filter_period + janela abr–mai)
import data_loader as dl  # noqa: E402

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #
FIGURES_DIR = dl.REPO_ROOT / "outputs" / "figuras"
OUT_NAME = "g4_disponibilidade_estacoes_abr_mai_2024.png"

TITLE = "Disponibilidade de dados — Estações pluviométricas (abr-mai 2024)"

# Estações de precipitação na ordem de exibição (topo → base).
PRECIP_STATIONS: tuple[dl.Station, ...] = tuple(
    s for s in dl.STATIONS if s.kind == "precipitacao"
)
_STATION_BY_CODE = {s.code: s for s in PRECIP_STATIONS}

# Verde = dado presente; vermelho = ausente (NaN). Contraste forte de propósito.
COLOR_PRESENTE = "#1a9850"
COLOR_AUSENTE = "#d73027"


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #
def load_precip(processed_dir: str | Path = dl.PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Carrega os CSVs das estações de precipitação em ``{codigo: DataFrame}``."""
    processed_dir = Path(processed_dir)
    frames: dict[str, pd.DataFrame] = {}
    for station in PRECIP_STATIONS:
        path = processed_dir / f"{station.kind}_{station.code}.csv"
        frames[station.code] = pd.read_csv(path, parse_dates=["datetime"])
    return frames


# --------------------------------------------------------------------------- #
# Disponibilidade
# --------------------------------------------------------------------------- #
def availability(df: pd.DataFrame, value_col: str = "precipitacao_mm") -> pd.Series:
    """Série booleana indexada por ``datetime``: ``True`` onde há dado, ``False`` se NaN."""
    series = df.sort_values("datetime").set_index("datetime")[value_col]
    return series.notna()


def availability_stats(avail: pd.Series) -> dict:
    """Resumo da disponibilidade: total, presentes, ausentes e percentuais."""
    total = int(avail.size)
    presentes = int(avail.sum())
    ausentes = total - presentes
    pct_disp = 100.0 * presentes / total if total else float("nan")
    pct_ausente = 100.0 * ausentes / total if total else float("nan")
    return {
        "total": total,
        "presentes": presentes,
        "ausentes": ausentes,
        "pct_disponivel": pct_disp,
        "pct_ausente": pct_ausente,
    }


def print_availability(stats_by_code: dict[str, dict]) -> None:
    """Imprime a tabela de disponibilidade por estação no período."""
    print(f"\nDisponibilidade — {ar.PERIOD_START} a {ar.PERIOD_END}")
    print(f"{'estação':>10} {'leituras':>9} {'ausentes':>9} "
          f"{'disp.%':>8} {'ausen.%':>8}")
    for code, s in stats_by_code.items():
        print(f"{code:>10} {s['total']:>9} {s['ausentes']:>9} "
              f"{s['pct_disponivel']:>8.1f} {s['pct_ausente']:>8.1f}")


# --------------------------------------------------------------------------- #
# Gráfico
# --------------------------------------------------------------------------- #
def plot_availability(
    avail_by_code: dict[str, pd.Series],
    stats_by_code: dict[str, dict],
    out_path: str | Path,
    order: tuple[str, ...] | None = None,
) -> Path:
    """Faixas temporais de disponibilidade (verde=dado, vermelho=NaN), uma por estação."""
    out_path = Path(out_path)
    codes = order if order is not None else tuple(avail_by_code)
    n = len(codes)
    lane_h = 0.8  # altura preenchida de cada faixa (deixa folga entre faixas)

    fig, ax = plt.subplots(figsize=(12, 1.7 * n + 1.6))
    yticks, ylabels = [], []
    for i, code in enumerate(codes):
        avail = avail_by_code[code]
        x = avail.index
        base = n - 1 - i  # primeira da lista no topo
        # Pinta toda a faixa de vermelho (ausente) e sobrepõe verde onde há dado:
        # garante carpete contínuo sem frestas brancas nas transições.
        ax.fill_between(x, base, base + lane_h, color=COLOR_AUSENTE, step="post")
        ax.fill_between(x, base, base + lane_h, where=avail.to_numpy(),
                        color=COLOR_PRESENTE, step="post")

        pct = stats_by_code[code]["pct_disponivel"]
        center = base + lane_h / 2
        yticks.append(center)
        ylabels.append(f"Estação {code}\n{pct:.1f}% disponível")
        ax.text(0.5, center, f"{pct:.0f}% disponível", transform=ax.get_yaxis_transform(),
                ha="center", va="center", fontsize=13, fontweight="bold",
                color="white")

    ax.set_xlim(pd.Timestamp(ar.PERIOD_START), pd.Timestamp(ar.PERIOD_END))
    ax.set_ylim(0, n)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%b"))
    ax.set_xlabel("Tempo (abril–maio 2024)")
    ax.set_title(TITLE, fontweight="bold")

    legend_handles = [
        mpatches.Patch(color=COLOR_PRESENTE, label="com dado"),
        mpatches.Patch(color=COLOR_AUSENTE, label="ausente (NaN)"),
    ]
    ax.legend(handles=legend_handles, loc="upper center",
              bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out_path


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
def main(
    processed_dir: str | Path = dl.PROCESSED_DIR,
    figures_dir: str | Path = FIGURES_DIR,
) -> Path:
    """Pipeline: carrega, recorta abr–mai/2024, calcula, plota e imprime."""
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    frames = load_precip(processed_dir)
    avail_by_code: dict[str, pd.Series] = {}
    stats_by_code: dict[str, dict] = {}
    for code, df in frames.items():
        value_col = _STATION_BY_CODE[code].value_column
        window = ar.filter_period(df)
        avail = availability(window, value_col)
        avail_by_code[code] = avail
        stats_by_code[code] = availability_stats(avail)

    print_availability(stats_by_code)

    order = tuple(s.code for s in PRECIP_STATIONS)
    out = plot_availability(avail_by_code, stats_by_code, figures_dir / OUT_NAME, order)
    print(f"\nFigura salva em: {out}")
    return out


if __name__ == "__main__":
    # Console Windows (cp1252) pode falhar com acentos; força UTF-8 se possível.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
