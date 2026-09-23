# Como contribuir

Obrigado pelo interesse! Toda ajuda é bem vinda: novas fontes de dados, correções, documentação e relatos de problemas.

## Ambiente

```bash
git clone https://github.com/Rafaxdz-1000/dadosimob
cd dadosimob
pip install -e ".[dev]"
pytest -m "not network"   # testes offline
pytest -m network         # testes que acessam as fontes reais
```

## Adicionando uma nova cidade de ITBI

1. Crie `src/dadosimob/itbi/<sigla>.py` seguindo o modelo de `sp.py`: funções `list_files`, `read` e `clean`, com as mesmas colunas padronizadas sempre que o dado existir.
2. Crie testes com uma planilha sintética pequena em `tests/` (não suba arquivos oficiais inteiros).
3. Documente a fonte, a cobertura e as particularidades no README.

## Padrões

* Nomes de colunas em português, snake_case, sem acentos.
* Nada de dados pessoais: se uma fonte trouxer CPF ou CNPJ de pessoa física, descarte a coluna.
* Seja educado com os servidores públicos: use o cache e evite requisições em paralelo.
* Rode `ruff check .` antes de abrir o pull request.
