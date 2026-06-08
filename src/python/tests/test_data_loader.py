"""Testes do data_loader (pytest)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Permite importar o módulo irmão sem instalar o pacote.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data_loader as dl  # noqa: E402

# Cabeçalho com "Mês" acentuado, como nos arquivos reais (ISO-8859-1).
HEADER = "   Dia   M\xeas   Ano   Hora   Chuva"

# Duas linhas normais e uma com o sentinela -1 (ausente), no mesmo
# formato de largura fixa / espaços à esquerda do dataset.
DATA_LINES = [
    "    01    07  2022    00        0.000000",
    "    01    07  2022    13        0.400000",
    "    02    07  2022    00       -1.000000",
]


def _write_raw(path: Path, *, header: bool) -> Path:
    """Escreve um arquivo cru sintético (ISO-8859-1, CRLF)."""
    lines = ([HEADER] if header else []) + DATA_LINES
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode(dl.ENCODING))
    return path


@pytest.fixture
def raw_with_header(tmp_path: Path) -> Path:
    return _write_raw(tmp_path / "com_header.txt", header=True)


@pytest.fixture
def raw_no_header(tmp_path: Path) -> Path:
    return _write_raw(tmp_path / "sem_header.txt", header=False)


# --------------------------------------------------------------------------- #
# Detecção de cabeçalho
# --------------------------------------------------------------------------- #
def test_has_header_true(raw_with_header: Path) -> None:
    assert dl._has_header(raw_with_header) is True


def test_has_header_false(raw_no_header: Path) -> None:
    assert dl._has_header(raw_no_header) is False


# --------------------------------------------------------------------------- #
# Leitura crua
# --------------------------------------------------------------------------- #
def test_read_raw_skips_header(raw_with_header: Path) -> None:
    df = dl.read_raw(raw_with_header)
    assert list(df.columns) == dl.RAW_COLUMNS
    assert len(df) == len(DATA_LINES)  # cabeçalho descartado
    assert df.iloc[0].to_dict() == {
        "dia": 1,
        "mes": 7,
        "ano": 2022,
        "hora": 0,
        "valor": 0.0,
    }


def test_read_raw_without_header(raw_no_header: Path) -> None:
    df = dl.read_raw(raw_no_header)
    assert len(df) == len(DATA_LINES)  # nenhuma linha perdida
    assert df.iloc[1]["valor"] == pytest.approx(0.4)


def test_read_raw_dtypes(raw_no_header: Path) -> None:
    df = dl.read_raw(raw_no_header)
    assert all(str(df[c].dtype) == "int64" for c in ["dia", "mes", "ano", "hora"])
    assert str(df["valor"].dtype) == "float64"


# --------------------------------------------------------------------------- #
# datetime
# --------------------------------------------------------------------------- #
def test_add_datetime(raw_no_header: Path) -> None:
    df = dl.add_datetime(dl.read_raw(raw_no_header))
    assert df["datetime"].iloc[1] == pd.Timestamp("2022-07-01 13:00:00")
    assert df["datetime"].iloc[2] == pd.Timestamp("2022-07-02 00:00:00")
    assert pd.api.types.is_datetime64_any_dtype(df["datetime"])


# --------------------------------------------------------------------------- #
# Limpeza de ausentes
# --------------------------------------------------------------------------- #
def test_clean_missing_converts_sentinel(raw_no_header: Path) -> None:
    df = dl.clean_missing(dl.read_raw(raw_no_header))
    assert df["valor"].isna().sum() == 1  # apenas a linha -1
    assert pd.isna(df["valor"].iloc[2])
    assert df["valor"].iloc[0] == 0.0  # zero legítimo preservado


def test_clean_missing_does_not_mutate_input(raw_no_header: Path) -> None:
    original = dl.read_raw(raw_no_header)
    dl.clean_missing(original)
    assert original["valor"].iloc[2] == -1.0  # entrada intacta


# --------------------------------------------------------------------------- #
# Pipeline por estação + escrita
# --------------------------------------------------------------------------- #
def test_load_station_pipeline(tmp_path: Path) -> None:
    station = dl.Station("2650035", "precipitacao", "precipitacao_mm", "mm")
    _write_raw(tmp_path / "2650035.txt", header=True)

    df = dl.load_station(station, raw_dir=tmp_path)
    assert list(df.columns) == [
        "datetime",
        "dia",
        "mes",
        "ano",
        "hora",
        "precipitacao_mm",
    ]
    assert df["precipitacao_mm"].isna().sum() == 1


def test_save_processed_roundtrip(tmp_path: Path) -> None:
    station = dl.Station("71350001", "nivel", "nivel_cm", "cm")
    _write_raw(tmp_path / "71350001.txt", header=False)

    df = dl.load_station(station, raw_dir=tmp_path)
    out = dl.save_processed(df, station, processed_dir=tmp_path / "processed")

    assert out.name == "nivel_71350001.csv"
    assert out.exists()

    reloaded = pd.read_csv(out, parse_dates=["datetime"])
    assert len(reloaded) == len(df)
    assert reloaded["nivel_cm"].isna().sum() == 1  # NaN sobrevive ao CSV


def test_main_creates_all_outputs(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    for station in dl.STATIONS:
        _write_raw(raw / f"{station.code}.txt", header=(station.kind == "precipitacao"))

    outputs = dl.main(raw_dir=raw, processed_dir=tmp_path / "processed")
    assert len(outputs) == len(dl.STATIONS)
    assert all(p.exists() for p in outputs)


# --------------------------------------------------------------------------- #
# Integração com os arquivos reais (pulado se ausentes)
# --------------------------------------------------------------------------- #
# Contagens medidas no dataset real (linhas de dados / valores -1).
REAL_EXPECTATIONS = {
    "2650035": (19752, 1275),
    "83967": (19752, 5784),
    "71350001": (19752, 64),
    "70719960": (19251, 7288),
}


@pytest.mark.parametrize("station", dl.STATIONS, ids=lambda s: s.code)
def test_real_files(station: dl.Station) -> None:
    raw_path = dl.RAW_DIR / f"{station.code}.txt"
    if not raw_path.exists():
        pytest.skip(f"arquivo real ausente: {raw_path}")

    expected_rows, expected_missing = REAL_EXPECTATIONS[station.code]
    df = dl.load_station(station)

    assert len(df) == expected_rows
    assert int(df[station.value_column].isna().sum()) == expected_missing
    assert df["datetime"].is_monotonic_increasing
    assert not df["datetime"].isna().any()
