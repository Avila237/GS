"""Testes da análise da enchente (pytest)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analise_enchente_rs as ar  # noqa: E402
import data_loader as dl  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures sintéticas (todas dentro da janela abr–mai/2024)
# --------------------------------------------------------------------------- #
def _hourly(start: str, periods: int, value_col: str, value: float) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    return pd.DataFrame({"datetime": idx, value_col: [value] * periods})


@pytest.fixture
def precip_48h() -> pd.DataFrame:
    return _hourly("2024-04-01", 48, "precipitacao_mm", 1.0)


@pytest.fixture
def nivel_48h() -> pd.DataFrame:
    return _hourly("2024-04-01", 48, "nivel_cm", 300.0)


# --------------------------------------------------------------------------- #
# Recorte de período
# --------------------------------------------------------------------------- #
def test_filter_period_bounds() -> None:
    df = pd.DataFrame({
        "datetime": pd.to_datetime(
            ["2024-03-31 23:00", "2024-04-01 00:00", "2024-05-31 23:00", "2024-06-01 00:00"]
        ),
        "nivel_cm": [1, 2, 3, 4],
    })
    out = ar.filter_period(df)
    assert list(out["nivel_cm"]) == [2, 3]  # extremos fora ficam de fora


def test_filter_period_does_not_mutate() -> None:
    df = pd.DataFrame({
        "datetime": pd.to_datetime(["2024-04-10 00:00", "2024-01-01 00:00"]),
        "nivel_cm": [10, 20],
    })
    ar.filter_period(df)
    assert len(df) == 2  # entrada preservada (resto não descartado)


# --------------------------------------------------------------------------- #
# Cálculos
# --------------------------------------------------------------------------- #
def test_daily_accumulated(precip_48h: pd.DataFrame) -> None:
    daily = ar.daily_accumulated(precip_48h, "precipitacao_mm")
    assert len(daily) == 2  # dois dias
    assert daily.iloc[0] == pytest.approx(24.0)  # 24h de 1mm
    assert daily.iloc[1] == pytest.approx(24.0)


def test_daily_accumulated_all_nan_day_is_nan() -> None:
    df = _hourly("2024-04-01", 24, "precipitacao_mm", float("nan"))
    daily = ar.daily_accumulated(df, "precipitacao_mm")
    assert pd.isna(daily.iloc[0])  # min_count=1 evita virar zero


def test_rolling_accumulated_24h(precip_48h: pd.DataFrame) -> None:
    roll = ar.rolling_accumulated(precip_48h, "precipitacao_mm")
    assert pd.isna(roll.iloc[0])  # janela incompleta no início
    assert roll.iloc[-1] == pytest.approx(24.0)  # 24h de 1mm


def test_build_correlation_frame(precip_48h, nivel_48h) -> None:
    merged = ar.build_correlation_frame(precip_48h, nivel_48h)
    assert list(merged.columns) == ["precip_24h_mm", "nivel_cm"]
    assert not merged.isna().any().any()  # NaN do warm-up removidos
    assert (merged["nivel_cm"] == 300.0).all()


def test_describe_period() -> None:
    df = pd.DataFrame({
        "datetime": pd.to_datetime(["2024-04-01", "2024-04-02", "2024-04-03"]),
        "nivel_cm": [100.0, 200.0, 300.0],
    })
    stats = ar.describe_period({"71350001": df})
    s = stats["71350001"]
    assert s["value_col"] == "nivel_cm"
    assert s["min"] == 100.0
    assert s["max"] == 300.0
    assert s["media"] == pytest.approx(200.0)
    assert s["ausentes"] == 0


# --------------------------------------------------------------------------- #
# Gráficos (salvam PNG não-vazio)
# --------------------------------------------------------------------------- #
def test_plot_river_level(nivel_48h: pd.DataFrame, tmp_path: Path) -> None:
    out = ar.plot_river_level(nivel_48h, tmp_path / "g1.png")
    assert out.exists() and out.stat().st_size > 0


def test_plot_daily_precip(precip_48h: pd.DataFrame, tmp_path: Path) -> None:
    daily = ar.daily_accumulated(precip_48h, "precipitacao_mm")
    out = ar.plot_daily_precip(daily, tmp_path / "g2.png")
    assert out.exists() and out.stat().st_size > 0


def test_plot_precip_vs_level(tmp_path: Path) -> None:
    # frame com variância nos dois eixos -> correlação bem definida
    merged = pd.DataFrame(
        {"precip_24h_mm": [0.0, 5.0, 10.0, 20.0], "nivel_cm": [150.0, 300.0, 450.0, 600.0]}
    )
    out = ar.plot_precip_vs_level(merged, tmp_path / "g3.png")
    assert out.exists() and out.stat().st_size > 0


# --------------------------------------------------------------------------- #
# Integração com os CSVs reais (pulado se ausentes)
# --------------------------------------------------------------------------- #
def test_main_integration(tmp_path: Path) -> None:
    missing = [
        s.code for s in dl.STATIONS
        if not (dl.PROCESSED_DIR / f"{s.kind}_{s.code}.csv").exists()
    ]
    if missing:
        pytest.skip(f"CSVs processados ausentes: {missing}")

    outputs = ar.main(figures_dir=tmp_path)
    assert len(outputs) == 3
    assert all(p.exists() and p.stat().st_size > 0 for p in outputs)
