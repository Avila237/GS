"""modelo_preditivo.py — Previsão de risco de enchente 6h à frente (POC).

Faz o merge de precipitação (estação 2650035) e nível do rio (estação
71350001), constrói features hidrológicas com defasagem (a correlação
contemporânea chuva×nível é fraca, r=0.13, pois o rio responde com atraso)
e treina um classificador para PREVER o risco daqui a HORIZON_HOURS horas.

Por que prever o futuro:
    O alvo é a classe de risco em t+6h (nível deslocado 6 posições para a
    frente, depois classificado). Assim `nivel_atual` torna-se uma feature
    LEGÍTIMA — ajuda a antecipar o nível futuro sem determiná-lo
    trivialmente. Numa versão anterior o alvo era o risco no instante atual,
    derivado do próprio nível atual: isso era vazamento de alvo e dava
    F1=1.0 enganoso. Agora o F1 cai — esperado e honesto, pois prever o
    futuro é uma tarefa de verdade.

    ML aqui é complementar, não core (ver context.md). Mantido simples.

Uso:
    python modelo_preditivo.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend headless
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_loader as dl  # noqa: E402

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #
FIGURES_DIR = dl.REPO_ROOT / "outputs" / "figuras"
PRECIP_STATION = "2650035"
RIVER_STATION = "71350001"

# Horizonte de previsão: quantas horas à frente o modelo prevê o risco.
HORIZON_HOURS = 6

# Limiares de risco (cm) ESTIMADOS do histórico do nível — NÃO são cotas
# oficiais da ANA. Convenção: intervalos fechados à esquerda (right=False),
# isto é, BAIXO<300, MEDIO[300,400), ALTO[400,500), CRITICO>=500.
RISK_BINS = [-np.inf, 300, 400, 500, np.inf]
RISK_LABELS = ["BAIXO", "MEDIO", "ALTO", "CRITICO"]

FEATURES = [
    "precipitacao_acum_24h",
    "precipitacao_acum_48h",
    "precipitacao_acum_72h",
    "taxa_subida_cm_h",
    "nivel_atual",
]
RANDOM_STATE = 42


@dataclass
class EvalResult:
    """Resultado da avaliação do melhor modelo."""

    model_name: str
    model: object
    accuracy: float
    f1_weighted: float
    confusion: np.ndarray
    labels: list[str]
    importances: pd.Series
    y_test: pd.Series
    y_pred: np.ndarray


# --------------------------------------------------------------------------- #
# Carga e features
# --------------------------------------------------------------------------- #
def load_merged(processed_dir: str | Path = dl.PROCESSED_DIR) -> pd.DataFrame:
    """Carrega os 2 CSVs e faz merge por datetime (inner join)."""
    processed_dir = Path(processed_dir)
    precip = pd.read_csv(
        processed_dir / f"precipitacao_{PRECIP_STATION}.csv", parse_dates=["datetime"]
    )[["datetime", "precipitacao_mm"]]
    nivel = pd.read_csv(
        processed_dir / f"nivel_{RIVER_STATION}.csv", parse_dates=["datetime"]
    )[["datetime", "nivel_cm"]]
    return (
        precip.merge(nivel, on="datetime", how="inner")
        .sort_values("datetime")
        .reset_index(drop=True)
    )


def classify_risk(nivel: pd.Series) -> pd.Series:
    """Deriva a classe de risco a partir do nível (cm)."""
    return pd.cut(nivel, bins=RISK_BINS, labels=RISK_LABELS, right=False)


def build_features(merged: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering + alvo futuro (t+HORIZON_HOURS).

    Assume amostragem horária regular (os CSVs do loader são contínuos), de
    modo que ``shift(6)`` corresponde a 6 horas no passado e ``shift(-6)`` a
    6 horas no futuro. O ``dropna`` remove o aquecimento (NaN no início, das
    janelas/taxa) e a cauda (NaN no fim, onde o alvo futuro não existe).
    """
    df = merged.sort_values("datetime").set_index("datetime")
    precip = df["precipitacao_mm"]
    nivel = df["nivel_cm"]

    out = pd.DataFrame(index=df.index)
    out["precipitacao_acum_24h"] = precip.rolling("24h", min_periods=20).sum()
    out["precipitacao_acum_48h"] = precip.rolling("48h", min_periods=40).sum()
    out["precipitacao_acum_72h"] = precip.rolling("72h", min_periods=60).sum()
    out["taxa_subida_cm_h"] = (nivel - nivel.shift(6)) / 6.0
    out["nivel_atual"] = nivel
    # Alvo = risco daqui a HORIZON_HOURS horas (prevê o FUTURO, sem vazamento).
    out["risco"] = classify_risk(nivel.shift(-HORIZON_HOURS))
    return out.dropna().reset_index()


# --------------------------------------------------------------------------- #
# Treino e avaliação
# --------------------------------------------------------------------------- #
def train_evaluate(
    features: pd.DataFrame, test_size: float = 0.25, random_state: int = RANDOM_STATE
) -> EvalResult:
    """Treina DecisionTree e RandomForest e devolve o de maior F1 (weighted)."""
    X = features[FEATURES]
    y = features["risco"].astype(str)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    candidates = {
        "DecisionTree": DecisionTreeClassifier(
            max_depth=8, random_state=random_state, class_weight="balanced"
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=100, max_depth=12, random_state=random_state,
            class_weight="balanced", n_jobs=-1,
        ),
    }

    best: tuple | None = None  # (name, clf, f1, pred)
    for name, clf in candidates.items():
        clf.fit(X_train, y_train)
        pred = clf.predict(X_test)
        f1 = f1_score(y_test, pred, average="weighted", labels=RISK_LABELS, zero_division=0)
        print(f"  {name}: F1(weighted)={f1:.3f}")
        if best is None or f1 > best[2]:
            best = (name, clf, f1, pred)

    name, clf, f1, pred = best
    return EvalResult(
        model_name=name,
        model=clf,
        accuracy=accuracy_score(y_test, pred),
        f1_weighted=f1,
        confusion=confusion_matrix(y_test, pred, labels=RISK_LABELS),
        labels=RISK_LABELS,
        importances=pd.Series(clf.feature_importances_, index=FEATURES),
        y_test=y_test,
        y_pred=pred,
    )


# --------------------------------------------------------------------------- #
# Gráficos e relatório
# --------------------------------------------------------------------------- #
def plot_confusion(result: EvalResult, out_path: str | Path) -> Path:
    """Salva a matriz de confusão como PNG."""
    out_path = Path(out_path)
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(
        confusion_matrix=result.confusion, display_labels=result.labels
    ).plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"Matriz de confusão — {result.model_name} (previsão t+{HORIZON_HOURS}h)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_feature_importance(result: EvalResult, out_path: str | Path) -> Path:
    """Salva a importância das features como PNG."""
    out_path = Path(out_path)
    fig, ax = plt.subplots(figsize=(8, 4))
    result.importances.sort_values().plot.barh(ax=ax, color="#2c7fb8")
    ax.set_title(f"Importância das features — {result.model_name} (previsão t+{HORIZON_HOURS}h)")
    ax.set_xlabel("Importância")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def print_metrics(result: EvalResult) -> None:
    """Imprime acurácia, F1, matriz de confusão e importâncias."""
    print(f"\nModelo selecionado: {result.model_name}")
    print(f"Acurácia:      {result.accuracy:.3f}")
    print(f"F1 (weighted): {result.f1_weighted:.3f}")
    print("\nMatriz de confusão (linhas=real, colunas=previsto):")
    print("          " + " ".join(f"{lbl:>8}" for lbl in result.labels))
    for lbl, row in zip(result.labels, result.confusion):
        print(f"{lbl:>9} " + " ".join(f"{v:>8}" for v in row))
    print("\nImportância das features:")
    for feat, imp in result.importances.sort_values(ascending=False).items():
        print(f"  {feat:>22}: {imp:.3f}")


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
def main(
    processed_dir: str | Path = dl.PROCESSED_DIR,
    figures_dir: str | Path = FIGURES_DIR,
) -> EvalResult:
    """Pipeline: carrega, gera features, treina, avalia, plota e reporta."""
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    features = build_features(load_merged(processed_dir))
    print(f"Previsão de risco {HORIZON_HOURS}h à frente")
    print(f"Amostras após feature engineering: {len(features)}")
    print("Distribuição de classes (alvo futuro):")
    print(features["risco"].value_counts().reindex(RISK_LABELS).to_string())

    print("\nComparação de modelos:")
    result = train_evaluate(features)
    print_metrics(result)

    cm_path = plot_confusion(result, figures_dir / "modelo_matriz_confusao.png")
    fi_path = plot_feature_importance(result, figures_dir / "modelo_feature_importance.png")
    print(f"\nGráficos salvos em {figures_dir}:")
    print(f"  - {cm_path.name}")
    print(f"  - {fi_path.name}")
    return result


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # acentos no console Windows
    except (AttributeError, ValueError):
        pass
    main()
