"""Testes do modelo preditivo (pytest)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data_loader as dl  # noqa: E402
import modelo_preditivo as mp  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures sintéticas
# --------------------------------------------------------------------------- #
def _synthetic_merged(periods: int = 100) -> pd.DataFrame:
    """Série horária regular: chuva constante 1mm, nível subindo 6 cm/h."""
    idx = pd.date_range("2022-07-01", periods=periods, freq="h")
    nivel = 100.0 + 6.0 * np.arange(periods)  # taxa exata de 6 cm/h
    return pd.DataFrame(
        {"datetime": idx, "precipitacao_mm": 1.0, "nivel_cm": nivel}
    )


@pytest.fixture
def features_synthetic() -> pd.DataFrame:
    """Features separáveis cobrindo as 4 classes (nível longe das bordas)."""
    rng = np.random.default_rng(0)
    levels = np.repeat([250.0, 350.0, 450.0, 550.0], 40)
    levels = levels + rng.normal(0, 5, levels.size)  # ruído << distância à borda
    df = pd.DataFrame(
        {
            "precipitacao_acum_24h": rng.normal(10, 3, levels.size),
            "precipitacao_acum_48h": rng.normal(20, 5, levels.size),
            "precipitacao_acum_72h": rng.normal(30, 7, levels.size),
            "taxa_subida_cm_h": rng.normal(2, 1, levels.size),
            "nivel_atual": levels,
        }
    )
    df["risco"] = mp.classify_risk(df["nivel_atual"]).astype(str)
    return df


@pytest.fixture
def trained_result(features_synthetic: pd.DataFrame) -> mp.EvalResult:
    return mp.train_evaluate(features_synthetic, test_size=0.3, random_state=0)


# --------------------------------------------------------------------------- #
# Target / classificação
# --------------------------------------------------------------------------- #
def test_classify_risk_boundaries() -> None:
    vals = pd.Series([100, 299, 300, 350, 399, 400, 499, 500, 600])
    got = list(mp.classify_risk(vals).astype(str))
    assert got == [
        "BAIXO", "BAIXO", "MEDIO", "MEDIO", "MEDIO",
        "ALTO", "ALTO", "CRITICO", "CRITICO",
    ]


# --------------------------------------------------------------------------- #
# Feature engineering
# --------------------------------------------------------------------------- #
def test_build_features_values() -> None:
    feat = mp.build_features(_synthetic_merged(100))
    assert list(feat.columns) == ["datetime"] + mp.FEATURES + ["risco"]
    last = feat.iloc[-1]
    assert last["precipitacao_acum_24h"] == pytest.approx(24.0)  # 24h de 1mm
    assert last["precipitacao_acum_48h"] == pytest.approx(48.0)
    assert last["precipitacao_acum_72h"] == pytest.approx(72.0)
    assert last["taxa_subida_cm_h"] == pytest.approx(6.0)  # nível sobe 6 cm/h


def test_build_features_drops_warmup_and_tail() -> None:
    merged = _synthetic_merged(100)
    feat = mp.build_features(merged)
    assert len(feat) < len(merged)  # aquecimento (início) descartado
    assert not feat[mp.FEATURES].isna().any().any()  # sem NaN nas features
    # cauda também descartada: alvo futuro inexiste nas últimas HORIZON_HOURS.
    horizonte = pd.Timedelta(hours=mp.HORIZON_HOURS)
    assert feat["datetime"].max() <= merged["datetime"].max() - horizonte


def test_target_is_six_hours_ahead() -> None:
    """O alvo deve refletir o nível FUTURO (t+6h), não o atual."""
    periods = 120
    idx = pd.date_range("2022-07-01", periods=periods, freq="h")
    nivel = np.full(periods, 200.0)  # BAIXO no presente...
    nivel[80:] = 600.0  # ...mas vira CRITICO a partir de t=80
    merged = pd.DataFrame(
        {"datetime": idx, "precipitacao_mm": 1.0, "nivel_cm": nivel}
    )
    feat = mp.build_features(merged).set_index("datetime")

    row = feat.loc[idx[74]]  # t+6h aponta para o nível em t=80 (=600)
    assert row["nivel_atual"] == 200.0  # presente ainda é BAIXO
    assert str(row["risco"]) == "CRITICO"  # alvo é o futuro -> CRITICO


# --------------------------------------------------------------------------- #
# Treino / split / predição
# --------------------------------------------------------------------------- #
def test_train_evaluate_outputs(trained_result: mp.EvalResult) -> None:
    res = trained_result
    assert res.model_name in ("DecisionTree", "RandomForest")
    assert 0.0 <= res.f1_weighted <= 1.0
    assert res.confusion.shape == (4, 4)
    assert set(res.importances.index) == set(mp.FEATURES)


def test_train_evaluate_separable_is_accurate(trained_result: mp.EvalResult) -> None:
    # nível determina a classe -> problema fácil -> alta acurácia
    assert trained_result.accuracy > 0.8
    # e o nível deve ser a feature mais importante
    assert trained_result.importances.idxmax() == "nivel_atual"


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def test_plot_confusion(trained_result: mp.EvalResult, tmp_path: Path) -> None:
    out = mp.plot_confusion(trained_result, tmp_path / "cm.png")
    assert out.exists() and out.stat().st_size > 0


def test_plot_feature_importance(trained_result: mp.EvalResult, tmp_path: Path) -> None:
    out = mp.plot_feature_importance(trained_result, tmp_path / "fi.png")
    assert out.exists() and out.stat().st_size > 0


# --------------------------------------------------------------------------- #
# Integração com os CSVs reais (pulado se ausentes)
# --------------------------------------------------------------------------- #
def _real_csvs_present() -> bool:
    return all(
        (dl.PROCESSED_DIR / f"{kind}_{code}.csv").exists()
        for kind, code in [("precipitacao", mp.PRECIP_STATION), ("nivel", mp.RIVER_STATION)]
    )


def test_load_merged_real() -> None:
    if not _real_csvs_present():
        pytest.skip("CSVs processados ausentes")
    merged = mp.load_merged()
    assert list(merged.columns) == ["datetime", "precipitacao_mm", "nivel_cm"]
    assert len(merged) > 0
    assert merged["datetime"].is_monotonic_increasing


def test_main_integration(tmp_path: Path) -> None:
    if not _real_csvs_present():
        pytest.skip("CSVs processados ausentes")
    res = mp.main(figures_dir=tmp_path)
    assert (tmp_path / "modelo_matriz_confusao.png").exists()
    assert (tmp_path / "modelo_feature_importance.png").exists()
    assert 0.0 <= res.f1_weighted <= 1.0


def test_real_prediction_has_no_leakage() -> None:
    """Sem vazamento: prevendo o futuro, o problema deixa de ser trivial."""
    if not _real_csvs_present():
        pytest.skip("CSVs processados ausentes")
    res = mp.main()

    # nivel_atual deixa de explicar 100% (era 1.0 com o alvo vazado)...
    assert res.importances["nivel_atual"] < 1.0
    # ...e as features de chuva passam a contribuir.
    precip_cols = ["precipitacao_acum_24h", "precipitacao_acum_48h", "precipitacao_acum_72h"]
    assert res.importances[precip_cols].sum() > 0.0
    # há erros fora da diagonal (não é mais perfeito).
    assert int(np.trace(res.confusion)) < int(res.confusion.sum())
