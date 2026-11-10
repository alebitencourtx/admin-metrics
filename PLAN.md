# Admin Metrics · Plano de solução e implantação

Data: 10/11/2026. Plano produzido antes da implementação e do deploy.

## Objetivo e organização

Monitorar a API Admin de métricas publicada pelos oito reportes operacionais Santander a cada duas horas, com coleta auditável, diagnóstico explicável, histórico e dashboard executivo no padrão visual Observatory. A medição própria alcança a API Admin; os demais endpoints são observados pelo reporte do banco, sem chamadas a APIs de clientes, consentimentos ou pagamentos.

Organização local:

```
teste-opendata/
  observatory-opendata/   projeto existente, incluindo seu .git e runtime
  admin-metrics/         projeto novo, independente
```

Decisão: dois repositórios. O existente mantém o remote `alebitencourtx/open-finance-observatory` e o endereço publicado. O novo será `alebitencourtx/admin-metrics`, com Pages próprio. A separação evita misturar ciclos de atualização, retenção, falhas e deploys. O compartilhamento é visual/conceitual, sem dependência de instalação entre os projetos.

## Análise independente da referência

A análise inicial foi lida em `C:/Users/alebi/Downloads/README-admin-metrics.md`. Seus números são evidências de outra coleta e não serão transcritos como dados atuais.

Conferência realizada em 10/11/2026:

- OAS oficial Admin 2.0.1: métricas agregadas, médias em ms, contadores do dia e `previousDays`, com primeiro elemento representando ontem. Os arrays podem ter até sete elementos anteriores; comprimentos diferentes serão tratados explicitamente.
- Consulta HTTPS verificada do Santander principal com `period=ALL` e `page-size=1000`: página 1 trouxe 112 identidades únicas; página 2 repetiu as mesmas 112. O servidor reescreveu `page-size` para 300, mas declarou duas páginas. É necessário deduplicar pela identidade do endpoint e reportar inconsistência de paginação.
- Na consulta, HTTP `Date` indicou 18:25 UTC e o corpo `requestTime` indicou 15:25Z. Isso comprova uma divergência no instante observado, não autoriza corrigir automaticamente todos os timestamps ou concluir a causa.
- O Confluence referenciado não ficou acessível pela ferramenta de consulta. Não serão afirmados SLAs ou enquadramentos regulatórios sem confirmação suficiente. A especificação técnica foi obtida da fonte oficial.

Conclusões da análise inicial que NÃO serão assumidas:

1. `errors` não permite identificar cada status HTTP de origem; `rejections` não prova 429 ou throttling específico.
2. Média de latência não é p95. Não haverá selo de conformidade regulatória derivado de médias.
3. Ausência de endpoint no reporte não comprova que a instituição não oferece o serviço.
4. 403 na coleta significa acesso recusado ao observador; não comprova indisponibilidade dos serviços nem identifica sozinho o mecanismo de restrição.
5. Um único horário com reporte vazio não demonstra uma janela fixa de consolidação diária.
6. Percentuais altos em amostras pequenas e agregados parciais exigem contexto de volume.

## Coleta e proveniência

- Catálogo explícito e versionado dos oito hosts: banco principal, Toro, CCVM, Aymoré, Getnet, Hyundai, Nissan e Renault. As duas marcas RCI ficam separadas; não deduplicar instituições por CNPJ.
- Validar o catálogo contra o Diretório oficial nesta implementação e preservar origem da configuração. Não descobrir URLs arbitrárias recebidas do usuário.
- HTTPS com verificação de certificado/hostname; timeout, retry limitado para transporte e 408/429/5xx selecionados, jitter e Retry-After limitado. Sem fallback inseguro, sem contornar bloqueios de acesso.
- No máximo quatro reportes simultâneos e uma requisição de cada reporte por vez. Paginação limitada por páginas, bytes e registros.
- Preservar resposta original, SHA-256, URL/parâmetros, HTTP, cabeçalho Date, instante UTC da coleta, duração observada, tentativa e erro.
- Deduplicar por `(reporter_id, endpoint)` dentro da coleta. Nunca somar páginas repetidas. Mudanças de valores entre páginas da mesma identidade ficam diagnosticadas; escolher a primeira observação e preservar ambas as evidências.
- Percorrer páginas enquanto houver identidade nova/indicação de continuidade. Parar em repetição, limite ou cobertura do total declarado; marcar conflitos de metadados. Distinguir cobertura por identidades de conformidade de paginação.
- Falha em um reporte não impede observar os outros. Uma execução totalmente sem dados publica diagnóstico de coleta e mantém as últimas métricas identificadas como antigas; nunca apresenta zero como substituto de ausência.

## Modelo temporal e retenção

Grãos principais:

- `runs`: execução, coleta, versão, contagens e estado.
- `probes`: tentativa HTTP por reporte/página, duração, status e referência bronze.
- `observations`: execução × reporte × endpoint, valores atuais, requestTime bruto, qualidade e dia de referência.
- `reported_history`: execução × reporte × endpoint × posição anterior; não somar as mesmas contagens diárias entre coletas.
- `intervals`: diferenças válidas entre observações cumulativas do mesmo dia e entidade.
- `incidents`: regra × entidade, abertura, atualização, recuperação e evidência.

UTC da coleta é o eixo autoritativo da nossa observação. O dia do reporte é ancorado no cabeçalho HTTP/instante de coleta em America/Sao_Paulo, identificado como uma convenção analítica; requestTime divergente é preservado e sinalizado, sem ajuste silencioso.

Guardar observações normalizadas por 30 dias (aproximadamente 360 ciclos de duas horas). Esse histórico é necessário para incidentes, mudanças e recuperação. Guardar bronze completo somente da coleta atual e anterior dentro do estado persistido. Os arrays anteriores do banco são contexto reportado, não observações nossas realizadas no passado.

Persistência em GitHub Releases: dois pacotes de estado aprovados, atual e anterior, com checksum. Cada pacote contém o histórico normalizado limitado e os dois bronzes recentes. Não versionar dados novos a cada duas horas no histórico Git. Compactar o estado; testar rotação e reprocessamento.

## Regras de monitoramento

Três classes independentes no painel:

1. **Coleta:** acesso recusado, timeout, HTTP de erro, TLS, resposta inválida, reporte ausente/vazio, duração da consulta e atraso de execução.
2. **Qualidade do reporte:** contadores inválidos, erro/rejeição superior às invocações, duplicação/conflito de páginas, arrays incompatíveis, uptime fora de [0,1], averageTPS maior que pico, horário divergente e resets/revisões de contadores.
3. **Sinais nos serviços reportados:** concentração de erros, taxa de erro/rejeição com amostra, médias elevadas e recorrência nos dias anteriores declarados.

Critérios analíticos iniciais, configuráveis e visíveis:

- Taxa de erro ≥ 5% com ≥ 100 invocações: atenção. ≥ 20% com ≥ 1.000 invocações: crítico. Nunca esconder o numerador e o denominador.
- Rejeição ≥ 5% com ≥ 100 invocações: atenção, com causa não determinada pelo payload.
- Média ≥ 2.000 ms com ≥ 100 invocações: atenção; ≥ 4.000 ms: crítico. Esses limiares são analíticos, não SLAs regulatórios.
- Aumento da média ≥ 2× a mediana de pelo menos três dias anteriores válidos: regressão indicada, com baseline e volume exibidos.
- Recorrência: pelo menos três dias anteriores com erro ≥ 5% e ≥ 100 invocações por dia. Rotular como recorrente no período reportado, sem diagnóstico causal.
- Erros concentrados: top cinco por quantidade e participação no total do recorte; não classificar apenas por percentual.
- Falha de coleta: atenção na primeira amostra; crítica após duas observações consecutivas. Recuperação após duas observações válidas consecutivas, com distinção de falha de acesso e falha de serviço.
- Incidentes de serviços devem preservar estados entre execuções e exigir duas amostras de recuperação abaixo do limiar. Identificar a criticidade provisória da primeira observação e a persistência nas seguintes.
- Se não houver observação nova por mais de três horas, indicar atualização atrasada no próprio navegador. Não prometer disponibilidade contínua com amostragem de duas horas.

Intervalos: só calcular deltas de contadores cumulativos em observações do mesmo dia de referência. Diminuição de contador é reset/revisão, não volume negativo nem recuperação. Contadores inválidos ou sem denominador deixam taxa nula. Não somar snapshots acumulados do dia. Não derivar média intervalar ou p95 de médias cumulativas sem base suficiente.

## Dashboard e documentação

HTML/CSS/JavaScript local no padrão Observatory: navegação lateral clicável, rolagem contínua e seção ativa sincronizada. Layout navy/teal, tipografia legível, tabelas com rolagem interna, teclado, estados vazios, filtros, exportação e impressão.

Seções planejadas:

- Panorama: estado das fontes, observação atual, tráfego declarado, erros/rejeições, média ponderada e incidentes.
- Incidentes: severidade, regra, evidência, primeira/última observação, recuperação e estado de confirmação.
- Tendências: histórico de observações próprias, sem somar acumulados; série diária reportada separada e explicitamente rotulada.
- Endpoints: busca, reporte, família, amostra, erro, rejeição, média, uptime declarado e detalhes históricos.
- Coleta: HTTP e duração observada do Admin, integridade/paginação e freshness; esses tempos não são latências dos serviços de cliente.
- Qualidade: inconsistências e impactos sobre os indicadores.
- Metodologia: contratos, fórmulas, limites, configuração e fonte.

Gráficos de tendência e rankings devem permitir ler valores, unidades e amostras, além de selecionar endpoint/reporte. Detalhamento preserva URL declarada e hashes. Nunca usar cores/status sem legenda.

Entregar também documentação funcional/técnica HTML única, autocontida, com arquitetura, fluxo e ER, regras, operação, stack e limitações. Atualizar a documentação com evidências reais da implantação.

## Stack e agendamento

Python 3.11/3.12, HTTPX, Arrow/Parquet, DuckDB e SQL para análise; JavaScript nativo e SVG/HTML/CSS para consumo estático. Bibliotecas isoladas por projeto. A escala prevista não justifica um cluster.

GitHub Actions em repositório público, runner padrão Linux. Agendamento a cada duas horas com minuto deslocado para reduzir disputa (por exemplo, `17 */2 * * *`, UTC), mais `workflow_dispatch`. Push republica sem criar uma coleta enganosa. Concurrency compartilhada impede corrida entre coleta e deploy.

Agendamentos do GitHub são best effort: podem atrasar e, em repositórios públicos sem atividade, podem ser desabilitados pela plataforma. O painel mostrará a idade real dos dados. Não criar automação do aplicativo Codex para vigiar jobs; acompanhar os jobs desta implementação até o término.

Coleta defeituosa deve continuar visível: persistir eventos de falha e histórico, conservar a última observação boa por reporte como contexto antigo. Corrupção do estado ou falha estrutural bloqueia publicação e preserva o estado anterior. Pages e Releases não são uma transação distribuída; registrar recibo de publicação e procedimento de recuperação.

## Sequência de execução

1. Escrever este plano e registrar as evidências iniciais.
2. Mover integralmente o projeto existente para `observatory-opendata`, mantendo .git/remote e verificando testes e dependências.
3. Criar `admin-metrics`, contratos, catálogo, coletor, armazenamento e transformação.
4. Testar paginação repetida/conflitante, falhas isoladas, meia-noite, resets, taxas inválidas, histórico, incidentes, recuperação e retenção.
5. Gerar dashboard e documentação com coleta real; validar navegação, filtros, detalhes, gráficos e exportação no navegador.
6. Criar repositório público e Pages, publicar estado inicial e ativar o agendamento de duas horas.
7. Executar o workflow real, conferir Pages/estado/retention e garantir que o Observatory anterior permanece publicado.

## Critérios de aceite

- Os dois projetos estão nas pastas solicitadas, com repositórios independentes e sem perda do projeto anterior.
- Plano existe antes de implantação; hipóteses da análise inicial são distinguidas de observações verificadas.
- O monitor consulta os oito reportes, registra falhas por fonte e preserva evidência, sem chamar endpoints de clientes reportados.
- Atualização remota de duas horas configurada e acionamento manual disponível; primeira execução real concluída.
- Histórico limitado e recuperação testados; incidentes e deltas não confundem dias parciais, resets, ausência e zero.
- Dashboard e documentação abrem na raiz do Pages novo; navegação e gráficos validados; site anterior continua disponível.
- CI, testes de risco e integridade aprovados; limites não homologados são declarados.

## Referências primárias

- [OAS Admin 2.0.1](https://raw.githubusercontent.com/OpenBanking-Brasil/openapi/main/swagger-apis/admin/2.0.1.yml)
- [Diretório oficial](https://data.directory.openbankingbrasil.org.br/participants)
- [Informações gerais Admin — referência a validar quando acessível](https://openfinancebrasil.atlassian.net/wiki/spaces/OF/pages/429588501)
- [Eventos e limites de agendamento do GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
