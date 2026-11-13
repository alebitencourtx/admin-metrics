# Uso e interpretação do dashboard

Revisão: 13/11/2026; interface 1.2.0. [Abrir painel](https://alebitencourtx.github.io/admin-metrics/).

## Comece pelo contexto temporal

Leia separadamente **última tentativa**, **últimos dados válidos** e **dia de referência**. Uma tentativa HTTP recente sem métricas não renova a idade dos dados. Após duas horas sem dados válidos, o aviso de idade é recalculado no navegador.

**DADOS ANTERIORES** significa que chamadas, taxa, média e ranking pertencem a um único ciclo completo anterior, explicitamente datado. A saúde das fontes e os incidentes continuam mostrando a última tentativa. Não se somam silenciosamente fontes de dias ou ciclos diferentes. Selecionar uma fonte saudável pode avançar seu panorama individual, mesmo quando o panorama conjunto permanece anterior.

Sem ciclo completo retido para o recorte, os indicadores ficam indisponíveis. Isso não equivale a zero tráfego. Tráfego zero realmente informado em um reporte utilizável continua sendo zero.

## As oito seções

| Seção | Como interpretar / usar |
|---|---|
| Panorama executivo | Fontes válidas refletem a tentativa atual; chamadas, erro, média e ranking usam o ciclo indicado. O ranking prioriza quantidade de erros, não somente percentual |
| Incidentes | Compare severidade, confirmação, regra, evidência e amostra. Recuperando ainda não é resolvido; ausência não prova saúde |
| Tendências | Janela de 72h de observações próprias. Selecione erro, média ou chamadas. Não some acumulados entre pontos |
| Endpoints | Busca/família/ordenação e páginas de 25 linhas; data/freshness identificam contexto antigo ou parcial |
| Saúde da coleta | HTTP e duração da consulta ao Admin, registros e diagnóstico da tentativa atual |
| Monitor de execuções | Matriz extração × API, últimos três dias, mais recentes primeiro e páginas de 12 execuções |
| Qualidade do reporte | Flags de conteúdo e comparabilidade; um endpoint pode ter várias ocorrências |
| Metodologia | Fórmulas, limiares, fontes e limites de interpretação |

## Monitor de execuções

[Abrir diretamente o monitor](https://alebitencourtx.github.io/admin-metrics/#execucoes). Cada célula distingue dados válidos, **HTTP 200 vazio**, falha HTTP, erro de transporte e reporte inválido/incompleto. O cabeçalho do run informa fontes com dados / total.

Clique numa API para abrir HTTP final, registros, horário, tentativas, duração, bytes, diagnóstico e SHA. Captura e tentativa HTTP são números distintos: uma fonte pode ter recapturas após vazio e retries HTTP dentro delas. Todos continuam pertencendo a uma única extração analítica.

O vínculo com o Actions é gravado nas novas coletas. Nos runs antigos, só aparece quando metadados de uma Release aprovada comprovam a associação; não se adivinha a execução por horário.

O painel é estático: mostra resultados publicados, não andamento ao vivo antes do deploy. Para acompanhar um job ainda em execução, abra o Actions. Barras de rolagem internas preservam a matriz em telas menores.

## Filtros, detalhes e exportação

- Reporte é filtro global; também reduz colunas do monitor. Cartões de fonte aplicam esse filtro.
- Estado de incidente afeta a lista de incidentes. Métrica afeta a tendência.
- Busca, família e ordenação afetam tabela de endpoints e CSV, não todo o painel.
- Ranking abre a evidência do ciclo usado naquele panorama. A tabela abre o último contexto disponível do endpoint; datas tornam a diferença explícita.
- Detalhe separa observações próprias de D−1/D−2/D−3 declarados pelo banco. O estado preserva até sete posições para baseline/recorrência.
- CSV exporta todas as linhas filtradas, não só a página de 25; usa UTF-8/BOM, `;`, aspas e proteção de prefixos de fórmula. Campos `reporter_id`, `fresh`, `source_complete` e proveniência permitem interpretar contexto.

Gráficos não inventam pontos em runs vazios. Lacunas maiores que 1,5h, ausência e mudança de dia interrompem linhas. Se ainda não há 72h de coleta, o período não observado fica vazio.

## Exemplos de leitura

| Situação | Conclusão permitida |
|---|---|
| HTTP 200 com zero registros | A fonte respondeu sem métricas utilizáveis; não prova zero chamadas ou serviço saudável |
| Nissan 503 e demais fontes vazias | Coleta indisponível; o panorama pode conservar o último ciclo completo anterior |
| 1.000 chamadas / 100 erros | 10% no acumulado declarado do dia; atenção conforme regra atual |
| Média 4.500 ms com amostra mínima | Sinal crítico por média; não p95 nem conclusão regulatória |
| Duas detecções consecutivas | Persistência no reporte; pode repetir o mesmo cumulativo |
| Run verde no Actions | Processamento/publicação concluídos; consultar o resumo de saúde para saber se houve dados |

Cores têm rótulos textuais. HTTP de coleta não mede diretamente os serviços listados. Serviços podem se sobrepor entre reportes; o agregado não representa necessariamente transações únicas. Causa de rejeição, status HTTP dos erros de serviços, participação de mercado e conformidade não são inferidos.
