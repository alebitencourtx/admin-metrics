# Evidências de validação

## Antes da implantação

- Migração do projeto anterior: repositório íntegro, remote preservado e 67 testes aprovados após reinstalar o pacote editável na nova pasta.
- Catálogo novo: oito correspondências URL/CNPJ no Diretório oficial, comprovante em `config/catalog-evidence.json`.
- Coleta real local: oito HTTP 200 e 276 endpoints; nenhuma chamada aos serviços de clientes listados.
- Testes automatizados: cenários de zeros/nulos/contadores impossíveis, horário/dia, resets, deduplicação, retry e 403, recuperação de incidentes, falha estrutural preservando publicação, falha total das fontes, retenção, reprocessamento, ZIP corrompido/path traversal e promoção após deploy.
- Navegador: panorama, filtro Santander, busca recurring-payments, detalhe com D−1…D−6, exportação CSV, navegação ativa, manual com busca/estado vazio e layout móvel a 390 px sem overflow horizontal de página.
- Ensaio sintético local: 360 ciclos × 276 registros = 99.360 observações; build Arrow/DuckDB/Parquet/HTML em 1,573 s, payload 26.136.648 bytes. Dados altamente repetitivos derivados da primeira coleta para testar a escala, sem publicação; não é benchmark de tráfego, variabilidade ou rede. Não estabelece SLA.

As execuções remotas, o estado aprovado e as URLs publicadas serão conferidos após o primeiro deploy. O diretório `artifacts/benchmark` é ignorado e não integra o site público.
