from datetime import date

import pandas as pd
import pytest

from dadosimob._text import parse_br_date, parse_br_number
from dadosimob.itbi import sp


def test_read_workbook(workbook):
    df = sp.read(workbook)
    assert len(df) == 6  # blank row and non-transaction sheets are skipped
    assert set(df["mes_referencia"].dt.month) == {1, 2}
    row = df.iloc[1]
    assert row["valor_transacao"] == 1_200_000.0
    assert row["data_transacao"] == pd.Timestamp("2024-01-15")
    assert row["sql"] == "1000100022"
    assert row["cep"] == "3104000"
    assert (df["codigo_ibge"] == "3550308").all()


def test_columns_are_canonical(workbook):
    df = sp.read(workbook)
    for col in sp.COLUMNS:
        assert col in df.columns, col
    assert {"mes_referencia", "tipo_imovel", "preco_m2", "codigo_ibge"} <= set(df.columns)


def test_property_type_and_price_m2(workbook):
    df = sp.read(workbook)
    assert df["tipo_imovel"].tolist() == ["apartamento", "casa", "terreno", "comercial", "apartamento", "garagem"]
    assert df.loc[0, "preco_m2"] == 10_000.0
    assert df.loc[2, "preco_m2"] == 1_200.0  # land uses terrain area


def test_filter_months(workbook):
    df = sp.read(workbook, months=[2])
    assert len(df) == 2
    assert (df["mes_referencia"] == pd.Timestamp("2024-02-01")).all()


def test_clean(workbook):
    df = sp.read(workbook)
    cleaned = sp.clean(df)
    assert "R ERRO" not in cleaned["logradouro"].tolist()
    sales = sp.clean(df, only_sales=True)
    assert "R DA MOOCA" not in sales["logradouro"].tolist()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("R$ 1.234.567,89", 1234567.89), ("1234,5", 1234.5), ("12,5%", 12.5), ("1.234.567", 1234567.0),
     (1500, 1500.0), ("", None), ("-", None), ("abc", None), (float("nan"), None)],
)
def test_parse_br_number(raw, expected):
    assert parse_br_number(raw) == expected


def test_parse_br_date():
    assert parse_br_date("15/01/2024") == date(2024, 1, 15)
    assert parse_br_date("2024-01-15 00:00:00") == date(2024, 1, 15)
    assert parse_br_date(45306) == date(2024, 1, 15)
    assert parse_br_date("nada") is None


@pytest.mark.parametrize(
    ("name", "expected"),
    [("JAN-2024", date(2024, 1, 1)), ("Março 2023", date(2023, 3, 1)), ("DEZ-2019", date(2019, 12, 1)),
     ("Tabela de USOS", None), ("EXPLICAÇÕES", None)],
)
def test_sheet_period(name, expected):
    assert sp.sheet_period(name) == expected


PAGE = """
<ul>
<li>2026 (<a href="https://prefeitura.sp.gov.br/documents/d/fazenda/guias-de-itbi-pagas-27082026-xls-xlsx">Excel/xlsx</a>)
 (<a href="http://prefeitura.sp.gov.br/x/GUIAS%20DE%20ITBI%20PAGAS%20ODS.ods">ODS</a>)</li>
<li>2024 (<a href="/cidade/secretarias/upload/fazenda/arquivos/itbi/GUIAS-DE-ITBI-PAGAS-2024.xlsx">Excel/xlsx</a>)</li>
<li>2019 (<a href="/cidade/secretarias/upload/fazenda/arquivos/itbi/ITBI_Setembro_2022/GUIAS_DE_ITBI_PAGAS_(2019).xlsx">Excel/xlsx</a>)</li>
</ul>
"""


def test_parse_source_page():
    files = sp.parse_source_page(PAGE)
    xlsx = {f.year: f.url for f in files if f.format == "xlsx"}
    assert set(xlsx) == {2019, 2024, 2026}
    assert xlsx[2024] == "https://prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/GUIAS-DE-ITBI-PAGAS-2024.xlsx"
    assert xlsx[2026].endswith("27082026-xls-xlsx")
    assert xlsx[2019].endswith("GUIAS_DE_ITBI_PAGAS_(2019).xlsx")  # year in folder name must not confuse


@pytest.mark.network
def test_list_files_live():
    files = sp.list_files()
    assert any(f.year == 2024 for f in files)


def test_cli(workbook, tmp_path, capsys):
    from dadosimob.cli import main

    out = tmp_path / "saida.csv"
    assert main(["itbi-sp", "--arquivo", str(workbook), "--limpar", "--apenas-vendas", "-o", str(out)]) == 0
    df = pd.read_csv(out)
    assert len(df) == 4  # drops the too cheap shop and the donation
    assert "linhas salvas" in capsys.readouterr().out
