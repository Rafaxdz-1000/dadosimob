"""Command line interface: ``dadosimob itbi-sp --ano 2024 -o itbi.csv``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .itbi import sp


def _cmd_itbi_sp(args: argparse.Namespace) -> int:
    if args.listar:
        for f in sp.list_files():
            print(f"{f.year}\t{f.url}")
        return 0
    if args.ano is None and args.arquivo is None:
        print("Informe --ano ou --arquivo", file=sys.stderr)
        return 2
    source = args.arquivo if args.arquivo else args.ano
    df = sp.read(source, months=args.mes)
    if args.limpar:
        df = sp.clean(df, only_sales=args.apenas_vendas)
    out = Path(args.saida)
    if out.suffix == ".parquet":
        df.to_parquet(out, index=False)
    else:
        df.to_csv(out, index=False)
    print(f"{len(df):,} linhas salvas em {out}".replace(",", "."))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dadosimob", description=__doc__)
    parser.add_argument("--version", action="version", version=f"dadosimob {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("itbi-sp", help="Transações com ITBI pago na cidade de São Paulo")
    p.add_argument("--ano", type=int, help="Ano de referência (ex.: 2024)")
    p.add_argument("--arquivo", help="Usar um .xlsx já baixado em vez de baixar")
    p.add_argument("--mes", type=int, action="append", help="Mês de referência (pode repetir)")
    p.add_argument("--limpar", action="store_true", help="Remover valores implausíveis")
    p.add_argument("--apenas-vendas", action="store_true", help="Com --limpar, manter só compra e venda")
    p.add_argument("--listar", action="store_true", help="Listar os arquivos publicados e sair")
    p.add_argument("-o", "--saida", default="itbi_sp.csv", help="Arquivo de saída (.csv ou .parquet)")
    p.set_defaults(func=_cmd_itbi_sp)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
