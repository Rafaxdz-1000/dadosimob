# dadosimob

**Dados públicos do mercado imobiliário brasileiro, prontos para análise.**
*Brazilian public real estate data, ready for analysis. [English below](#english).*

[![PyPI](https://img.shields.io/pypi/v/dadosimob.svg)](https://pypi.org/project/dadosimob/)
[![CI](https://github.com/Rafaxdz-1000/dadosimob/actions/workflows/ci.yml/badge.svg)](https://github.com/Rafaxdz-1000/dadosimob/actions/workflows/ci.yml)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)

Prefeituras e órgãos públicos publicam dados valiosos sobre imóveis, mas cada fonte tem seu formato: planilhas com uma aba por mês, cabeçalhos que mudam de um ano para outro, números no formato brasileiro e links que trocam de endereço. O `dadosimob` resolve isso e entrega um `pandas.DataFrame` limpo e padronizado.

## Instalação

```bash
pip install dadosimob
```

Para a versão em desenvolvimento: `pip install git+https://github.com/Rafaxdz-1000/dadosimob`.

## Fontes disponíveis

| Módulo | Dado | Cobertura | Origem |
|---|---|---|---|
| `dadosimob.itbi.sp` | Transações com ITBI pago | Cidade de São Paulo, 2006 até hoje (atualização mensal) | [Secretaria Municipal da Fazenda](https://prefeitura.sp.gov.br/web/fazenda/w/acesso_a_informacao/31501) |

Os 21 arquivos anuais publicados até agora (2006 a julho de 2026, 2.736.208 transações) são lidos por inteiro: todos os meses, com valor e data preenchidos em pelo menos 99,99% das linhas de cada ano. Próximas fontes no [roadmap](#roadmap).

## Uso rápido

```python
from dadosimob.itbi import sp

df = sp.read(2024)                    # baixa (com cache) e padroniza o ano inteiro
vendas = sp.clean(df, only_sales=True) # remove valores implausíveis e mantém só compra e venda

vendas.groupby("tipo_imovel")["preco_m2"].median()
```

Outras formas:

```python
sp.list_files()                 # anos publicados e seus links atuais
sp.read(2024, months=[1, 2, 3]) # só o primeiro trimestre
sp.read("meu_arquivo.xlsx")     # planilha que você já baixou
```

Pela linha de comando:

```bash
dadosimob itbi-sp --listar
dadosimob itbi-sp --ano 2024 --limpar --apenas-vendas -o itbi_2024.csv
```

### Colunas

Cada linha é uma Declaração de Transação Imobiliária (DTI) paga no mês de referência. As colunas originais viram nomes padronizados (`sql`, `logradouro`, `numero`, `bairro`, `cep`, `natureza_transacao`, `valor_transacao`, `data_transacao`, `valor_venal_referencia`, `base_calculo`, `tipo_financiamento`, `valor_financiado`, `area_terreno_m2`, `area_construida_m2`, `descricao_uso`, `descricao_padrao`, entre outras), e a biblioteca acrescenta:

* `mes_referencia`: mês em que o imposto foi pago (a aba de origem)
* `tipo_imovel`: `apartamento`, `casa`, `terreno`, `comercial`, `industrial`, `garagem` ou `outro`
* `preco_m2`: valor da transação dividido pela área construída (ou pela área do terreno, no caso de terrenos), só quando o imóvel inteiro é transmitido
* `codigo_ibge`: código IBGE do município

Números no formato brasileiro (`1.234,56`) e datas em texto ou no formato do Excel são convertidos automaticamente. `cep` (8 dígitos) e `sql` (11 dígitos) voltam como texto, com os zeros à esquerda que o Excel apaga.

Algumas abas do arquivo oficial vêm sem a linha de cabeçalho (em 2024, janeiro e outubro). Nesses casos a biblioteca usa o cabeçalho das outras abas do mesmo arquivo. Se uma aba mensal não puder ser lida, ela gera um aviso (`logging.WARNING`) em vez de sumir em silêncio. Nos arquivos de 2019 a 2022, a descrição do padrão vem rotulada como um segundo "ACC (IPTU)"; a biblioteca devolve cada dado na sua coluna.

### Boas práticas com o dado

* A data de pagamento do ITBI (`mes_referencia`) pode ser meses depois da `data_transacao`. Para séries de preço, prefira `data_transacao`.
* `valor_transacao` é declarado pelo contribuinte. `clean()` remove extremos, mas vale olhar a distribuição antes de concluir algo.
* Em 2024, quase metade das compras e vendas transmitiu só uma fração do imóvel (`proporcao_transmitida` abaixo de 100), como a unidade na planta registrada no lote-mãe, que pode aparecer como `terreno`. O arquivo não traz a área da fração, então `preco_m2` fica vazio nesses casos.
* A área é a área construída do cadastro do IPTU, não a área útil dos anúncios. Não compare `preco_m2` direto com preço de portal.
* `bairro` é texto livre e vem vazio em boa parte das linhas. Para recortes geográficos, prefira o CEP.
* Os arquivos oficiais não trazem transações de imóveis rurais nem as pagas via PPI.
* Os arquivos oficiais não contêm CPF ou CNPJ das partes.

## Roadmap

* ITBI de outras capitais que publicam uma linha por transação: Porto Alegre, Recife, Belo Horizonte, Fortaleza e Rio de Janeiro
* Renda domiciliar por setor censitário (IBGE, Censo 2022)
* Base CNPJ da Receita Federal com geocodificação por bairro
* Admissões e desligamentos por município (CAGED)

## Contribua

Cada cidade é um módulo independente: dá para contribuir sem conhecer o resto do código.

* [Tarefas para começar](https://github.com/Rafaxdz-1000/dadosimob/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
* [Cidades com a fonte oficial já conferida](https://github.com/Rafaxdz-1000/dadosimob/issues?q=is%3Aissue+is%3Aopen+label%3A%22nova+cidade%22)
* [Guia de contribuição](CONTRIBUTING.md), com o passo a passo para adicionar uma cidade

Conhece uma fonte pública que deveria estar aqui? [Sugira](https://github.com/Rafaxdz-1000/dadosimob/issues/new?template=nova-fonte.yml).

## Licença

Código sob [MIT](LICENSE). Os dados pertencem aos órgãos que os publicam; consulte os termos de cada fonte.

---

## English

`dadosimob` downloads Brazilian public real estate datasets and returns clean, standardized `pandas` DataFrames.

The first source is **ITBI São Paulo**: the property transfer tax declarations paid in the city of São Paulo since 2006, published monthly by the city's Finance Department as yearly Excel files with one sheet per month and headers that drift over time. `dadosimob` finds the current file links, caches downloads, detects header rows (and reuses them for sheets published without one), maps columns to stable snake_case names, parses Brazilian number and date formats, keeps the leading zeros of zip codes and property IDs, classifies property types and computes price per m² for whole-property transfers.

```bash
pip install dadosimob
```

```python
from dadosimob.itbi import sp

df = sp.clean(sp.read(2024), only_sales=True)
df.groupby("tipo_imovel")["preco_m2"].median()
```

Column names are kept in Portuguese to match the source documentation. The area behind `preco_m2` is the built area from the property tax registry, not the usable area quoted in listings, and `bairro` is free text that is often empty.

Each city is a self-contained module, so adding one needs no knowledge of the rest of the code. See the [good first issues](https://github.com/Rafaxdz-1000/dadosimob/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) and the [contributing guide](CONTRIBUTING.md) (in Portuguese; issues and pull requests in English are welcome).
