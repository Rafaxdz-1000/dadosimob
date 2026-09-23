"""ITBI transactions for the city of São Paulo (SP).

Source: Secretaria Municipal da Fazenda, "Dados das Transações Imobiliárias com
recolhimento de ITBI". One Excel workbook per year, one sheet per month. Each
row is one paid DTI (Declaração de Transação Imobiliária).

https://prefeitura.sp.gov.br/web/fazenda/w/acesso_a_informacao/31501

The published files carry no CPF/CNPJ of buyers or sellers.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import pandas as pd
import requests

from .. import _http
from .._text import normalize_label, parse_br_date, parse_br_number

log = logging.getLogger(__name__)

IBGE_CODE = "3550308"
SOURCE_PAGE = "https://prefeitura.sp.gov.br/web/fazenda/w/acesso_a_informacao/31501"

# Canonical column -> normalized header prefixes found in the official files.
# More specific prefixes come first; each source column is used only once.
COLUMNS: dict[str, tuple[str, ...]] = {
    "sql": ("n do cadastro sql", "no do cadastro sql", "numero do cadastro sql", "cadastro sql", "sql"),
    "logradouro": ("nome do logradouro", "logradouro"),
    "numero": ("numero",),
    "complemento": ("complemento",),
    "bairro": ("bairro",),
    "referencia": ("referencia",),
    "cep": ("cep",),
    "natureza_transacao": ("natureza de transacao", "natureza"),
    "valor_transacao": ("valor de transacao", "valor da transacao"),
    "data_transacao": ("data de transacao", "data da transacao"),
    "valor_venal_referencia_proporcional": ("valor venal de referencia proporcional",),
    "valor_venal_referencia": ("valor venal de referencia",),
    "proporcao_transmitida": ("proporcao transmitida",),
    "base_calculo": ("base de calculo",),
    "tipo_financiamento": ("tipo de financiamento",),
    "valor_financiado": ("valor financiado",),
    "cartorio": ("cartorio de registro", "cartorio"),
    "matricula": ("matricula do imovel", "matricula"),
    "situacao_sql": ("situacao do sql",),
    "area_terreno_m2": ("area do terreno",),
    "testada_m": ("testada",),
    "fracao_ideal": ("fracao ideal",),
    "area_construida_m2": ("area construida",),
    "uso_iptu": ("uso iptu",),
    "descricao_uso": ("descricao do uso",),
    "padrao_iptu": ("padrao iptu",),
    "descricao_padrao": ("descricao do padrao", "descricao do pardao"),  # FEV-2026 misspells it
    "acc_iptu": ("acc iptu", "acc"),
}

# Excel stores these codes as numbers and drops their leading zeros.
# SQL: setor (3) + quadra (3) + lote (4) + digito (1). Every CEP in the city starts with 0.
CODE_WIDTHS = {"sql": 11, "cep": 8}
_CODE_PUNCT = re.compile(r"[\s./-]")

NUMERIC = (
    "valor_transacao", "valor_venal_referencia", "valor_venal_referencia_proporcional",
    "proporcao_transmitida", "base_calculo", "valor_financiado", "area_terreno_m2",
    "testada_m", "fracao_ideal", "area_construida_m2",
)

# Ordered: first match wins. Applied to "descricao_uso".
# "APARTAMENTO EM CONDOMÍNIO (EXCETO VAGA)" must be an apartment, so apartment
# checks come before the parking space ones.
PROPERTY_TYPES: tuple[tuple[str, str], ...] = (
    ("apartamento", "apartamento"),
    ("flat", "apartamento"),
    ("vaga", "garagem"),
    ("garagem", "garagem"),
    ("residencia", "casa"),
    ("casa", "casa"),
    ("sobrado", "casa"),
    ("terreno", "terreno"),
    ("loja", "comercial"),
    ("escritorio", "comercial"),
    ("consultorio", "comercial"),
    ("comercio", "comercial"),
    ("servico", "comercial"),
    ("sala", "comercial"),
    ("hotel", "comercial"),
    ("industria", "industrial"),
    ("galp", "industrial"),
    ("armaz", "industrial"),
    ("deposito", "industrial"),
)

_MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


@dataclass(frozen=True)
class ItbiFile:
    year: int
    url: str
    format: str  # "xlsx" or "ods"


# ── Discovery ────────────────────────────────────────────────────────────────

_ANCHOR = re.compile(r"<a\b[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.I | re.S)
_YEAR = re.compile(r"\b(20\d{2})\b")
_TAGS = re.compile(r"<[^>]+>")


def parse_source_page(page_html: str, base_url: str = SOURCE_PAGE) -> list[ItbiFile]:
    """Extract the yearly file links from the Fazenda page HTML."""
    files: dict[tuple[int, str], ItbiFile] = {}
    for match in _ANCHOR.finditer(page_html):
        href, label = match.group(1), _TAGS.sub("", match.group(2)).lower()
        fmt = "xlsx" if "xlsx" in label or "excel" in label else "ods" if "ods" in label else None
        if fmt is None:
            continue
        before = _TAGS.sub(" ", page_html[max(0, match.start() - 400): match.start()])
        years = _YEAR.findall(before)
        if not years:
            continue
        year = int(years[-1])
        url = urljoin(base_url, html.unescape(href))
        files.setdefault((year, fmt), ItbiFile(year, url, fmt))
    return sorted(files.values(), key=lambda f: (f.year, f.format))


def list_files(fmt: str = "xlsx") -> list[ItbiFile]:
    """List the yearly files currently published by the Prefeitura."""
    resp = _http.get(SOURCE_PAGE)
    return [f for f in parse_source_page(resp.text) if f.format == fmt]


def download(year: int, *, cache_dir: Path | str | None = None, force: bool = False) -> Path:
    """Download the workbook for ``year`` (cached) and return its local path.

    The source page is read on every call, so a newly published file is picked up.
    When the page is unreachable or does not list the year, the most recent cached
    copy is used instead, with a warning.
    """
    cache = Path(cache_dir) if cache_dir else _http.default_cache_dir()
    name = f"itbi_sp_{year}.xlsx"
    try:
        url = _year_url(year)
    except (requests.RequestException, RuntimeError):
        cached = _cached_copy(cache, name)
        if cached is None:
            raise
        log.warning("Página da Fazenda inacessível; usando a cópia em cache %s", cached)
        return cached
    if url is None:
        cached = _cached_copy(cache, name)
        if cached is None:
            raise ValueError(f"Ano {year} não encontrado em {SOURCE_PAGE}")
        log.warning("Ano %s não listado em %s; usando a cópia em cache %s", year, SOURCE_PAGE, cached)
        return cached
    return _http.download(url, cache_dir=cache, filename=name, force=force)


def _year_url(year: int) -> str | None:
    # The page occasionally comes back without a year that is there a moment later.
    for _ in range(2):
        match = next((f for f in list_files() if f.year == year), None)
        if match:
            return match.url
    return None


def _cached_copy(cache: Path, name: str) -> Path | None:
    copies = sorted(cache.glob(f"*_{name}"), key=lambda p: p.stat().st_mtime)
    return copies[-1] if copies else None


# ── Parsing ──────────────────────────────────────────────────────────────────

def sheet_period(sheet_name: str) -> date | None:
    """Map sheet names such as ``"JAN-2024"`` or ``"Março 2024"`` to a date."""
    label = normalize_label(sheet_name)
    year = _YEAR.search(label)
    if not year:
        return None
    for token in label.split():
        month = _MONTHS.get(token[:3])
        if month:
            return date(int(year.group(1)), month, 1)
    return None


def map_columns(headers: Iterable[object]) -> dict[int, str]:
    """Return ``{column_index: canonical_name}`` for recognized headers."""
    normalized = [normalize_label(h) for h in headers]
    mapping: dict[int, str] = {}
    for canonical, prefixes in COLUMNS.items():
        for prefix in prefixes:
            idx = next(
                (i for i, h in enumerate(normalized)
                 if i not in mapping and h and (h == prefix or h.startswith(prefix + " "))),
                None,
            )
            if idx is not None:
                mapping[idx] = canonical
                break
    # The 2019 to 2022 files label "Descrição do padrão (IPTU)" as a second "ACC (IPTU)".
    # The real ACC (a year) is the last of the two.
    acc = [i for i, h in enumerate(normalized) if h == "acc iptu"]
    if len(acc) == 2 and "descricao_padrao" not in mapping.values():
        mapping[acc[0]] = "descricao_padrao"
        mapping[acc[1]] = "acc_iptu"
    return mapping


def _find_header(raw: pd.DataFrame, max_rows: int = 15) -> int | None:
    for i in range(min(max_rows, len(raw))):
        labels = {normalize_label(v) for v in raw.iloc[i].tolist()}
        text = " | ".join(labels)
        if "logradouro" in text and "valor de transacao" in text:
            return i
    return None


def _parse_sheet(
    raw: pd.DataFrame, period: date | None, header: list | None = None, *, name: str | None = None
) -> pd.DataFrame | None:
    """Parse one monthly sheet.

    ``header`` is used for sheets that have no header row of their own: the data
    starts at the first row and the columns follow the other sheets of the file.
    """
    if header is None:
        header_row = _find_header(raw)
        if header_row is None:
            return None
        header, start = raw.iloc[header_row].tolist(), header_row + 1
    else:
        start = 0
    mapping = map_columns(header)
    unmapped = [header[i] for i in range(len(header)) if i not in mapping and normalize_label(header[i])]
    if unmapped:
        log.warning("Aba %s: cabeçalhos não reconhecidos: %s", name or "?", ", ".join(str(h) for h in unmapped))
    body = raw.iloc[start:, list(mapping)].copy()
    body.columns = [mapping[i] for i in mapping]
    body = body.dropna(how="all")
    for col in NUMERIC:
        if col in body:
            body[col] = body[col].map(parse_br_number).astype("float64")
    if "data_transacao" in body:
        body["data_transacao"] = pd.to_datetime(body["data_transacao"].map(parse_br_date), errors="coerce")
    for col in ("sql", "cep", "numero", "uso_iptu", "padrao_iptu", "acc_iptu", "cartorio", "matricula"):
        if col in body:
            body[col] = body[col].map(lambda v, w=CODE_WIDTHS.get(col): _as_code(v, w)).astype("string")
    body.insert(0, "mes_referencia", pd.Timestamp(period) if period else pd.NaT)
    return body


def _first_header(sheets: dict[str, pd.DataFrame]) -> list | None:
    """Header row of the first sheet that has one."""
    for raw in sheets.values():
        row = _find_header(raw)
        if row is not None:
            return raw.iloc[row].tolist()
    return None


def _parse_headerless(raw: pd.DataFrame, period: date, header: list | None, name: str) -> pd.DataFrame | None:
    """Read a monthly sheet that lost its header row, if its layout matches the other sheets."""
    if header is not None and raw.shape[1] == len(header):
        parsed = _parse_sheet(raw, period, header=header, name=name)
        if parsed is not None and not parsed.empty and parsed["valor_transacao"].notna().mean() >= 0.5:
            log.info("Aba %s sem cabeçalho: usando o cabeçalho das outras abas", name)
            return parsed
    log.warning("Aba %s ignorada: não tem cabeçalho e o conteúdo não bate com as colunas das outras abas", name)
    return None


def _as_code(value: object, width: int | None = None) -> str | None:
    """Codes as text. With ``width``, restores the leading zeros Excel drops."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    digits = _CODE_PUNCT.sub("", text)
    if width and digits.isdigit() and len(digits) <= width:
        return digits.zfill(width)
    return text or None


def classify_property(description: object) -> str:
    """Group the IPTU use description into a simple property type."""
    label = normalize_label(description)
    if not label:
        return "outro"
    for fragment, kind in PROPERTY_TYPES:
        if fragment in label:
            return kind
    return "outro"


def read(
    source: int | str | Path,
    *,
    months: Iterable[int] | None = None,
    cache_dir: Path | str | None = None,
) -> pd.DataFrame:
    """Read ITBI SP transactions into a tidy DataFrame.

    ``source`` is a year (downloads the official file) or a path to a workbook
    you already have. ``months`` filters by reference month (1 to 12).

    Returns one row per paid DTI with standardized snake_case columns, plus
    ``mes_referencia``, ``tipo_imovel``, ``preco_m2`` and ``codigo_ibge``.
    """
    path = download(source, cache_dir=cache_dir) if isinstance(source, int) else Path(source)
    wanted = set(months) if months else None
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    header = _first_header(sheets)
    frames = []
    for name, raw in sheets.items():
        period = sheet_period(str(name))
        if wanted and (period is None or period.month not in wanted):
            continue
        parsed = _parse_sheet(raw, period, name=str(name))
        if parsed is None and period is not None:
            parsed = _parse_headerless(raw, period, header, str(name))
        if parsed is None:
            if period is None:
                log.debug("Aba ignorada (sem cabeçalho de transações): %s", name)
            continue
        log.info("Aba %s: %d linhas", name, len(parsed))
        frames.append(parsed)
    if not frames:
        raise ValueError(f"Nenhuma aba de transações encontrada em {path}")
    df = pd.concat(frames, ignore_index=True)
    df["tipo_imovel"] = df.get("descricao_uso", pd.Series(index=df.index, dtype=object)).map(classify_property)
    df["preco_m2"] = _price_per_m2(df)
    df["codigo_ibge"] = IBGE_CODE
    return df


def _price_per_m2(df: pd.DataFrame) -> pd.Series:
    price = df.get("valor_transacao")
    if price is None:
        return pd.Series(float("nan"), index=df.index)
    built = df.get("area_construida_m2", pd.Series(float("nan"), index=df.index))
    land = df.get("area_terreno_m2", pd.Series(float("nan"), index=df.index))
    area = built.where(built > 0, land.where(df["tipo_imovel"] == "terreno"))
    # A partial transfer (e.g. a unit sold on the parent lot of a new building) is priced
    # for a share, but the areas describe the whole property: no price per m² is possible.
    share = df.get("proporcao_transmitida", pd.Series(float("nan"), index=df.index))
    whole = share.isna() | (share >= 100)
    return (price / area.where((area > 0) & whole)).round(2)


def clean(
    df: pd.DataFrame,
    *,
    only_sales: bool = False,
    min_price: float = 10_000,
    max_price: float = 2_000_000_000,
    min_price_m2: float = 500,
    max_price_m2: float = 150_000,
) -> pd.DataFrame:
    """Drop implausible rows (price and price per m² outside sane ranges).

    With ``only_sales=True`` keeps only "compra e venda" transactions, which is
    usually what you want for market price analysis.
    """
    out = df
    if only_sales and "natureza_transacao" in out:
        out = out[out["natureza_transacao"].map(normalize_label).str.contains("compra e venda", na=False)]
    price = out["valor_transacao"]
    out = out[price.between(min_price, max_price)]
    ppm2 = out["preco_m2"]
    out = out[ppm2.isna() | ppm2.between(min_price_m2, max_price_m2)]
    return out.reset_index(drop=True)
