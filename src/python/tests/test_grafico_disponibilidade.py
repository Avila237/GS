"""Testes do gráfico de disponibilidade dos pluviômetros (pytest)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data_loader as dl  # noqa: E402
import grafico_disponibilidade as gd  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures sintéticas (dentro da janela abr–mai/2024)
# --------------------------------------------------------------------------- #
def _hourly_with_gaps(start: str, periods: int, nan_positions: set[int]) -> pd.DataFrame:
    """DataFrame horário de precipitação com NaN nas posições indicadas."""
    idx = pd.date_range(start, periods=periods, freq="h")
    vals = [float("nan") if i in nan_positions else 1.0 for i in range(periods)]
    return pd.DataFrame({"datetime": idx, "precipitacao_mm": vals})


@pytest.fixture
def precip_quase_cheio() -> pd.DataFrame:
    # 10 leituras, 1 ausente -> 90% disponível
    return _hourly_with_gaps("2024-04-01", 10, {3})


@pytest.fixture
def precip_tudo_nan() -> pd.DataFrame:
    # 10 leituras, todas ausentes -> 0% disponível
    return _hourly_with_gaps("2024-05-01", 10, set(range(10)))


# --------------------------------------------------------------------------- #
# Disponibilidade
# --------------------------------------------------------------------------- #
def test_availability_marca_nan(precip_quase_cheio: pd.DataFrame) -> None:
    avail = gd.availability(precip_quase_cheio)
    assert avail.dtype == bool
    assert avail.sum() == 9  # 9 presentes
    assert not avail.iloc[3]  # posição do NaN


def test_availability_ordena_por_datetime() -> None:
    df = pd.DataFrame({
        "datetime": pd.to_datetime(["2024-04-02 00:00", "2024-04-01 00:00"]),
        "precipitacao_mm": [float("nan"), 1.0],
    })
    avail = gd.availability(df)
    assert list(avail.index) == sorted(avail.index)  # índice cronológico
    assert avail.iloc[0]  # 01/04 (com dado) vem antes


def test_availability_stats_quase_cheio(precip_quase_cheio: pd.DataFrame) -> None:
    s = gd.availability_stats(gd.availability(precip_quase_cheio))
    assert s["total"] == 10
    assert s["presentes"] == 9
    assert s["ausentes"] == 1
    assert s["pct_disponivel"] == pytest.approx(90.0)
    assert s["pct_ausente"] == pytest.approx(10.0)


def test_availability_stats_tudo_nan(precip_tudo_nan: pd.DataFrame) -> None:
    s = gd.availability_stats(gd.availability(precip_tudo_nan))
    assert s["total"] == 10
    assert s["presentes"] == 0
    assert s["ausentes"] == 10
    assert s["pct_disponivel"] == pytest.approx(0.0)
    assert s["pct_ausente"] == pytest.approx(100.0)


# --------------------------------------------------------------------------- #
# Gráfico (salva PNG não-vazio)
# --------------------------------------------------------------------------- #
def test_plot_availability(
    precip_quase_cheio: pd.DataFrame,
    precip_tudo_nan: pd.DataFrame,
    tmp_path: Path,
) -> None:
    avail_by_code = {
        "2650035": gd.availability(precip_quase_cheio),
        "83967": gd.availability(precip_tudo_nan),
    }
    stats_by_code = {c: gd.availability_stats(a) for c, a in avail_by_code.items()}
    out = gd.plot_availability(
        avail_by_code, stats_by_code, tmp_path / "g4.png", order=("2650035", "83967")
    )
    assert out.exists() and out.stat().st_size > 0


# --------------------------------------------------------------------------- #
# Integração com os CSVs reais (pulado se ausentes)
# --------------------------------------------------------------------------- #
def test_main_integration(tmp_path: Path) -> None:
    missing = [
        s.code for s in gd.PRECIP_STATIONS
        if not (dl.PROCESSED_DIR / f"{s.kind}_{s.code}.csv").exists()
    ]
    if missing:
        pytest.skip(f"CSVs processados ausentes: {missing}")

    out = gd.main(figures_dir=tmp_path)
    assert out.exists() and out.stat().st_size > 0


def test_main_stats_batem_com_enunciado(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A estação 2650035 deve ficar ~93,6% disponível e a 83967 0% na janela."""
    missing = [
        s.code for s in gd.PRECIP_STATIONS
        if not (dl.PROCESSED_DIR / f"{s.kind}_{s.code}.csv").exists()
    ]
    if missing:
        pytest.skip(f"CSVs processados ausentes: {missing}")

    frames = gd.load_precip()
    stats = {}
    for code, df in frames.items():
        col = gd._STATION_BY_CODE[code].value_column
        stats[code] = gd.availability_stats(gd.availability(ar_filter(df), col))

    assert stats["2650035"]["pct_disponivel"] == pytest.approx(93.6, abs=0.1)
    assert stats["83967"]["pct_disponivel"] == pytest.approx(0.0, abs=0.01)


def ar_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Atalho para o recorte abr–mai usado pelo módulo (reaproveita a análise)."""
    return gd.ar.filter_period(df)
