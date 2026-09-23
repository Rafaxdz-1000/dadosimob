# Changelog

## 0.1.0 (2026)

* Primeira versão: módulo `dadosimob.itbi.sp` com descoberta de arquivos, download com cache, padronização de colunas, classificação de tipo de imóvel, preço por m² e limpeza.
* Linha de comando `dadosimob itbi-sp`.
* Validada contra os 21 arquivos anuais oficiais, de 2006 a julho de 2026 (2.736.208 transações):
  * abas mensais sem linha de cabeçalho (janeiro e outubro de 2024) são lidas com o cabeçalho das outras abas; aba mensal que não puder ser lida gera aviso;
  * nos arquivos de 2019 a 2022, a descrição do padrão vem rotulada como um segundo "ACC (IPTU)": cada dado volta na sua coluna (`descricao_padrao` e `acc_iptu`);
  * em fevereiro de 2026, o cabeçalho traz "Descrição do pardão (IPTU)": a coluna é reconhecida mesmo assim;
  * `cep` e `sql` mantêm os zeros à esquerda;
  * `preco_m2` fica vazio em transmissão parcial, em que o arquivo não traz a área da fração;
  * se a página da Fazenda falhar ou não listar o ano, a descoberta tenta de novo e, depois, usa a cópia em cache.
