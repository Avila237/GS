"""data_loader.py — Carrega e limpa os arquivos brutos do dataset UFRGS/Zenodo.

Os arquivos em ``data/raw/`` são de largura fixa, encoding ISO-8859-1 e
quebra de linha CRLF, com as colunas ``Dia``, ``Mês``, ``Ano``, ``Hora`` e
``Valor`` separadas por espaços. O valor ``-1`` é o sentinela de dado ausente.

O dataset mistura dois layouts:
- precipitação (mm): possui linha de cabeçalho;
- nível do rio (cm): **não** possui cabeçalho.

Este módulo lê cada arquivo, monta a coluna ``datetime``, troca ``-1`` por
``NaN`` e exporta CSVs limpos em ``data/processed/``.

Uso:
    python data_loader.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ENCODING = "ISO-8859-1"
MISSING_SENTINEL = -1.0

# Raiz do repositório: src/python/data_loader.py -> .../GS
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

# Nomes das 5 colunas brutas (independente de o arquivo ter ou não cabeçalho).
RAW_COLUMNS = ["dia", "mes", "ano", "hora", "valor"]


@dataclass(frozen=True)
class Station:
    """Metadados de uma estação/arquivo do dataset."""

    code: str  # nome do arquivo sem extensão
    kind: str  # "precipitacao" ou "nivel"
    value_column: str  # nome da coluna de valor no CSV de saída
    unit: str  # unidade de medida ("mm" ou "cm")


STATIONS: tuple[Station, ...] = (
    Station("2650035", "precipitacao", "precipitacao_mm", "mm"),
    Station("83967", "precipitacao", "precipitacao_mm", "mm"),
    Station("71350001", "nivel", "nivel_cm", "cm"),
    Station("70719960", "nivel", "nivel_cm", "cm"),
)


def _has_header(path: Path, encoding: str = ENCODING) -> bool:
    """Retorna ``True`` se a primeira linha for cabeçalho.

    Heurística: numa linha de dados o primeiro token é o dia (numérico);
    num cabeçalho é texto (ex.: ``Dia``).
    """
    with open(path, encoding=encoding) as fh:
        first = fh.readline().strip()
    if not first:
        return False
    first_token = first.split()[0]
    try:
        int(first_token)
    except ValueError:
        return True
    return False


def read_raw(path: str | Path, encoding: str = ENCODING) -> pd.DataFrame:
    """Lê um ``.txt`` de largura fixa em um DataFrame com as colunas brutas.

    Detecta automaticamente a presença de cabeçalho, já que os arquivos de
    nível do rio não têm e os de precipitação têm.
    """
    path = Path(path)
    skiprows = 1 if _has_header(path, encoding) else 0
    return pd.read_csv(
        path,
        sep=r"\s+",
        header=None,
        names=RAW_COLUMNS,
        skiprows=skiprows,
        encoding=encoding,
    )


def add_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona a coluna ``datetime`` a partir de dia/mês/ano/hora."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(
        {
            "year": df["ano"],
            "month": df["mes"],
            "day": df["dia"],
            "hour": df["hora"],
        }
    )
    return df


def clean_missing(df: pd.DataFrame, value_column: str = "valor") -> pd.DataFrame:
    """Substitui o sentinela ``-1`` por ``NaN`` na coluna de valor."""
    df = df.copy()
    df[value_column] = df[value_column].mask(df[value_column] == MISSING_SENTINEL)
    return df


def load_station(station: Station, raw_dir: str | Path = RAW_DIR) -> pd.DataFrame:
    """Carrega e limpa o arquivo de uma estação, devolvendo o DataFrame final."""
    path = Path(raw_dir) / f"{station.code}.txt"
    df = read_raw(path)
    df = add_datetime(df)
    df = clean_missing(df, "valor")
    df = df.rename(columns={"valor": station.value_column})
    cols = ["datetime", "dia", "mes", "ano", "hora", station.value_column]
    return df[cols]


def save_processed(
    df: pd.DataFrame, station: Station, processed_dir: str | Path = PROCESSED_DIR
) -> Path:
    """Salva o DataFrame limpo como CSV em ``processed_dir`` e devolve o caminho."""
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / f"{station.kind}_{station.code}.csv"
    df.to_csv(out_path, index=False)
    return out_path


def main(
    raw_dir: str | Path = RAW_DIR, processed_dir: str | Path = PROCESSED_DIR
) -> list[Path]:
    """Processa todas as estações e grava os CSVs limpos."""
    outputs: list[Path] = []
    for station in STATIONS:
        df = load_station(station, raw_dir)
        out_path = save_processed(df, station, processed_dir)
        missing = int(df[station.value_column].isna().sum())
        print(
            f"{station.code} ({station.kind}): {len(df)} linhas, "
            f"{missing} ausentes -> {out_path}"
        )
        outputs.append(out_path)
    return outputs


if __name__ == "__main__":
    main()
