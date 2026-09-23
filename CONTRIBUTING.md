# Como contribuir

Contribuições de qualquer tamanho entram: uma cidade nova, um ano validado, um exemplo, uma correção de texto. Se esta é a sua primeira contribuição em código aberto, este guia leva do fork ao pull request.

## Por onde começar

* [`good first issue`](https://github.com/Rafaxdz-1000/dadosimob/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22): tarefas pequenas, com critério de pronto.
* [`nova cidade`](https://github.com/Rafaxdz-1000/dadosimob/issues?q=is%3Aissue+is%3Aopen+label%3A%22nova+cidade%22): cidades com a fonte oficial já conferida.
* Conhece uma fonte que não está na lista? Abra uma issue com o modelo **Nova fonte de dados**.

Comente na issue antes de começar, para duas pessoas não fazerem a mesma coisa.

## Ambiente

```bash
# depois de fazer o fork no GitHub
git clone https://github.com/<seu-usuario>/dadosimob
cd dadosimob
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -m "not network"          # testes offline, rodam em segundos
pytest -m network                # testes que acessam as fontes reais
ruff check .
```

## Adicionar uma cidade

Cada cidade é um módulo independente em `src/dadosimob/itbi/`. Dá para contribuir sem conhecer o resto do código. O módulo de São Paulo, `sp.py`, é a referência.

### 1. O módulo

Crie `src/dadosimob/itbi/<cidade>.py` com um nome curto, minúsculo e sem acento (`rio`, `bh`, `poa`) e registre-o em `src/dadosimob/itbi/__init__.py`. O módulo expõe:

| Nome | O que é |
|---|---|
| `IBGE_CODE` | código IBGE do município, em texto (7 dígitos) |
| `SOURCE_PAGE` | endereço da página oficial de onde os arquivos saem |
| `read(source, *, cache_dir=None)` | recebe um ano (baixa o arquivo oficial, com cache) ou o caminho de um arquivo local e devolve um `pandas.DataFrame` |
| `list_files()` | opcional: os arquivos publicados, quando a fonte tem mais de um |
| `clean(df, ...)` | opcional: remove valores implausíveis, como `sp.clean` |

Reaproveite o que já existe:

* `dadosimob._http.download(url, cache_dir=..., filename=...)` baixa com cache, novas tentativas e o User-Agent da biblioteca. Nunca baixe o mesmo arquivo duas vezes.
* `dadosimob._text.parse_br_number("R$ 1.234,56")`, `parse_br_date("15/01/2024")` e `normalize_label("Área Construída")` tratam número, data e cabeçalho no formato brasileiro.

### 2. As colunas

Use os nomes de `sp.COLUMNS` sempre que o conceito existir na sua fonte: `valor_transacao`, `data_transacao`, `logradouro`, `numero`, `bairro`, `cep`, `natureza_transacao`, `area_construida_m2`, `area_terreno_m2` e os demais. Coluna que só a sua cidade tem: nome em português, snake_case, sem acento.

O mínimo para o pull request entrar:

* `valor_transacao`: float, em reais
* `data_transacao`: datetime
* `codigo_ibge`: texto

Quando a fonte traz área e uso do imóvel, acrescente também `tipo_imovel` (`apartamento`, `casa`, `terreno`, `comercial`, `industrial`, `garagem` ou `outro`) e `preco_m2`, que fica vazio quando só uma fração do imóvel foi transmitida.

### 3. Os testes

* Monte um arquivo sintético pequeno em `tests/conftest.py`, com as mesmas colunas do arquivo oficial e poucas linhas. Não suba o arquivo oficial.
* Teste pelo menos: colunas padronizadas, conversão de número e data, `codigo_ibge`.
* Achou uma armadilha no arquivo oficial (aba sem cabeçalho, código que perde o zero à esquerda, número em texto)? Escreva um teste que a reproduza.
* Um teste marcado com `@pytest.mark.network` confere que a fonte ainda responde.

### 4. Confira contra o arquivo oficial

Teste sintético só prova o que você imaginou. Rode o seu `read` no arquivo real e conte no pull request: quantas linhas, quantos meses e quanto de `valor_transacao` e `data_transacao` veio preenchido. Foi assim que apareceram as abas sem cabeçalho do arquivo de 2024 de São Paulo.

### 5. Documente

* Uma linha na tabela "Fontes disponíveis" do README.
* As particularidades da fonte em "Boas práticas com o dado".

A linha de comando (`dadosimob itbi-<cidade>`) é opcional e pode vir num pull request separado.

## Validar um ano de São Paulo

A página da Fazenda publica um arquivo por ano desde 2006, e o cabeçalho muda ao longo do tempo. Para validar um ano:

```python
from dadosimob.itbi import sp

df = sp.read(2015)
print(len(df), sorted(df["mes_referencia"].dt.month.unique()))
print(df[["valor_transacao", "data_transacao", "cep"]].notna().mean())
```

Conte no pull request (ou na issue do ano) o que saiu. Se algum mês sumir ou alguma coluna vier vazia, o pull request traz a correção e um teste que reproduz o problema.

## Padrões

* Nada de dados pessoais: se a fonte trouxer CPF, CNPJ de pessoa física ou nome das partes, descarte a coluna.
* Seja educado com os servidores públicos: use o cache e não faça requisições em paralelo.
* `ruff check .` e `pytest -m "not network"` passando antes de abrir o pull request.
* Issues, commits e pull requests podem ser em português ou em inglês.
* Pode usar assistente de IA. Quem responde pelo código é você: rode contra o arquivo oficial e diga no pull request o que conferiu.
