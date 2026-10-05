# Radar Concursos

Monitor automático de **concursos públicos brasileiros**: detecta editais recém-postados,
cadastra órgão, banca, vagas, salário, requisitos e links, e mantém tudo pesquisável por
**estado, área e curso** — tanto para **inscrições abertas** quanto para concursos
**previstos/autorizados** (edital ainda não saiu).

## Como funciona

```
Coletores (a cada 3h)  →  Triagem/classificação  →  Extração de campos  →  SQLite  →  Interface web
```

1. **Coletores** varrem as fontes em janelas de 2–3 dias (o que faz a detecção de
   "recém-postado": qualquer item novo na fonte entra como candidato).
2. **Triagem** (`app/classify.py`) decide se é concurso, descarta ruído (resultados,
   homologações, convocações) e define o status: `previsto → autorizado →
   edital_publicado → inscricoes_abertas`.
3. **Extração** (`app/extract.py`) baixa o PDF do edital quando existe e busca
   vagas, salário e datas por regex; manchetes de notícia também são mineradas
   (ex.: "edital autorizado com 200 vagas").
4. **Classificação** taggeia cada concurso com **área** (Saúde, Policial, Judiciária…),
   **cursos exigidos** (Direito, Enfermagem, Computação/TI…) e **UF/nível**.
5. Deduplicação por impressão digital (`órgão + UF + ano`) — o mesmo concurso visto
   em fontes diferentes é mesclado, mantendo histórico da primeira detecção.

## Fontes monitoradas

| Fonte | O que dá | Método |
|---|---|---|
| **DOU** (in.gov.br) | Editais e autorizações federais | busca JSON embutida no portal |
| **Querido Diário** (OKBR) | Diários oficiais municipais | API pública + download dos .txt |
| **FCC** | Concursos ativos da banca | HTML da listagem |
| **IBFC** | Concursos em andamento/abertos | HTML da listagem |
| **Google Notícias** | Detector de editais novos e concursos previstos (o "futuro") | RSS |

**De fora por enquanto** (bloqueio anti-bot / SPA — fase 2 com Playwright): Cebraspe, VUNESP, IDECAN.

## Como usar

```bash
pip install -r requirements.txt

# primeira coleta (leva alguns minutos; o Querido Diário é o mais lento)
python cli.py collect

# subir a interface web
python cli.py serve            # → http://127.0.0.1:8000

# conferir o que tem no banco
python cli.py stats

# coletar de fontes específicas
python cli.py collect --fonte dou,queridodiario
```

A interface tem abas (**Inscrições abertas / Editais publicados / Previstos e autorizados / Todos**),
filtros por **estado, área, curso e nível**, busca por texto e o botão **⟳ Buscar agora**
que dispara uma coleta na hora e mostra o resumo por fonte.

### Agendamento automático

O servidor já agenda coletas a cada 3 horas. Configurações por variável de ambiente:

- `CONCURSO_INTERVALO_HORAS=3` — intervalo da coleta (0 desliga o agendador)
- `CONCURSO_COLLECT_ON_START=1` — coleta logo ao subir o servidor

## Estrutura

```
cli.py                  comandos: collect / serve / stats
app/
  config.py             caminhos, UA, janelas de coleta
  classify.py           triagem, áreas, cursos, UF, nível
  database.py           SQLite (concursos, eventos_fonte, execucoes)
  extract.py            PDF → vagas/salário/datas
  ingest.py             pipeline: evento → triagem → extração → banco
  collectors/           dou, queridodiario, fcc, ibfc, googlenews (+ base.py)
  web/                  API FastAPI + interface estática
```

## Limitações honestas (fase 1)

- Vagas/salário são **best-effort** (regex); às vezes faltam — o link do edital oficial sempre acompanha.
- Cobertura municipal depende da inclusão do município no Querido Diário.
- As manchetes de notícia viram registros com menos campos; servem de alerta e apontam para a notícia.
- Colisões raras de dedupe podem mesclar concursos de órgãos com nome igual no mesmo estado/ano.

## Fase 2 (planejado)

- Playwright para Cebraspe/VUNESP/IDECAN e detalhamento por cargo (tabela do anexo).
- Classificação de requisitos por LLM (o pipeline já separa o ponto de encaixe em `processar`).
- Notificações (Telegram/e-mail) para concursos que batem com filtros salvos.
- Deploy em VPS para coleta 24/7.
