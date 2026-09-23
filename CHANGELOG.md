# Changelog

## 0.1.0 (2026)

* Primeira versão: módulo `dadosimob.itbi.sp` com descoberta de arquivos, download com cache, padronização de colunas, classificação de tipo de imóvel, preço por m² e limpeza.
* Linha de comando `dadosimob itbi-sp`.
* Validada contra os arquivos oficiais de 2024, 2025 e 2026:
  * abas mensais sem linha de cabeçalho (janeiro e outubro de 2024) são lidas com o cabeçalho das outras abas; aba mensal que não puder ser lida gera aviso;
  * `cep` e `sql` mantêm os zeros à esquerda;
  * `preco_m2` fica vazio em transmissão parcial, em que o arquivo não traz a área da fração;
  * se a página da Fazenda falhar ou não listar o ano, a descoberta tenta de novo e, depois, usa a cópia em cache.
