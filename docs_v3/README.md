# Documentação v3

Revisão de **15/11/2026** do Admin Metrics, gerada com a skill `project-html-docs` 1.6.0.

## Entregas

- `documentacao-v3.html` — manual completo, 14 capítulos.
- `documentacao-v3-resumida.html` — guia rápido, 6 capítulos.

Os dois arquivos são HTML único, offline, sem CDN, fontes remotas ou scripts externos.

## Autoria

- `document.json` + `content.md` — manual completo.
- `document-summary.json` + `content-summary.md` — guia rápido.

As fontes declaradas nos manifestos são relativas à raiz do repositório (`repoRoot: ".."`).

## Regerar

```powershell
node C:\Users\alebi\Documents\ChatGPT\teste-opendata\project-html-docs\scripts\build.mjs docs_v3\document.json --out docs_v3\documentacao-v3.html --force
node C:\Users\alebi\Documents\ChatGPT\teste-opendata\project-html-docs\scripts\build.mjs docs_v3\document-summary.json --out docs_v3\documentacao-v3-resumida.html --force
```

## Verificar

```powershell
node C:\Users\alebi\Documents\ChatGPT\teste-opendata\project-html-docs\scripts\verify.mjs docs_v3\document.json docs_v3\documentacao-v3.validation.json
node C:\Users\alebi\Documents\ChatGPT\teste-opendata\project-html-docs\scripts\verify.mjs docs_v3\document-summary.json docs_v3\documentacao-v3-resumida.validation.json
```

O `build.py` copia os dois HTMLs para `site/docs_v3/` durante a publicação do dashboard. A home do Pages referencia ambos.
