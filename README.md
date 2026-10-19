# Robótica API

![CI](https://github.com/Kauan-V-Marques/robotica-api-flask/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-8.0-47A248?logo=mongodb&logoColor=white)

API para organizar **competições de robótica**: cadastro de robôs por categoria, partidas de sumô, tomadas de tempo de seguidor de linha e **ranking calculado pelo próprio MongoDB** com pipelines de agregação.

Nasceu da minha experiência como capitão de eletrônica da equipe OmegaBotz, onde sempre precisávamos acompanhar a tabela das competições. Os dados de exemplo são fictícios.

O painel web que consome esta API está em [ranking-robotica-web](https://github.com/Kauan-V-Marques/ranking-robotica-web).

## Funcionalidades

- **Robôs** com categoria e peso validados (cada categoria tem um peso máximo)
- **Dois formatos de disputa:**
  - **partidas** (sumô 3 kg, 500 g e 100 g): vitória vale 3 pontos e empate vale 1. O desempate é por saldo de rounds e depois por vitórias
  - **tempo** (seguidor de linha): vale a melhor volta válida; voltas em que o robô saiu da pista não contam
- **Ranking** com posição compartilhada em caso de empate total (1º, 1º, 3º)
- **Estatísticas de carreira** de cada robô em todas as competições
- Validação com **Pydantic**, erros em JSON padronizado (400, 404, 409, 422) e CORS liberado para o painel web
- Comando `flask seed` que carrega uma competição de exemplo

## Agregação no MongoDB

O ranking do sumô transforma cada partida em dois "lados" (um por robô) e soma tudo no banco:

```python
[
    {"$match": {"event_id": event_id, "category": category}},
    {"$project": {"sides": [
        {"robot": "$robot_a", "for": "$score_a", "against": "$score_b"},
        {"robot": "$robot_b", "for": "$score_b", "against": "$score_a"},
    ]}},
    {"$unwind": "$sides"},
    {"$replaceRoot": {"newRoot": "$sides"}},
    {"$group": {
        "_id": "$robot",
        "wins":   {"$sum": {"$cond": [{"$gt": ["$for", "$against"]}, 1, 0]}},
        "draws":  {"$sum": {"$cond": [{"$eq": ["$for", "$against"]}, 1, 0]}},
        ...
    }},
    {"$addFields": {"points": {"$add": [{"$multiply": ["$wins", 3]}, "$draws"]}}},
    {"$lookup": {"from": "robots", "localField": "_id", "foreignField": "_id", "as": "robot"}},
    {"$sort": {"points": -1, "round_diff": -1, "wins": -1}},
]
```

O seguidor de linha usa `$min` para a melhor volta e `$setWindowFields` com `$rank` para a posição. O código completo está em [`robotica/stats.py`](robotica/stats.py).

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/robots/categories` | Categorias, peso máximo e formato |
| GET / POST | `/api/robots?category=&team=` | Lista / cadastra robôs |
| GET / PATCH / DELETE | `/api/robots/{id}` | Consulta / altera / exclui (se não tiver histórico) |
| GET | `/api/robots/{id}/stats` | Vitórias, empates, derrotas e aproveitamento |
| GET / POST | `/api/events` | Lista / cria competições |
| GET | `/api/events/{id}` | Competição com resumo por categoria |
| GET / POST | `/api/events/{id}/matches` | Partidas de sumô |
| POST | `/api/events/{id}/runs` | Tomada de tempo do seguidor de linha |
| GET | `/api/events/{id}/ranking?category=` | Classificação da categoria |
| GET | `/health` | Verifica a conexão com o banco |

Exemplo de `GET /api/events/{id}/ranking?category=seguidor_de_linha`:

```json
{
  "event": { "id": "6ad6...", "name": "Copa Sorocaba de Robotica 2026" },
  "category": { "code": "seguidor_de_linha", "name": "Seguidor de linha", "max_weight_g": 1000, "mode": "tempo" },
  "ranking": [
    { "position": 1, "robot": "Raio",   "team": "Equipe Delta", "best_ms": 17620, "average_ms": 18398, "valid_runs": 3 },
    { "position": 2, "robot": "Cometa", "team": "Equipe Alfa",  "best_ms": 18110, "average_ms": 18271, "valid_runs": 2 },
    { "position": 3, "robot": "Coruja", "team": "Equipe Gama",  "best_ms": 21004, "average_ms": 21004, "valid_runs": 1 }
  ]
}
```

## Como rodar

**Com Docker:**

```bash
docker compose up --build -d
docker compose exec api flask --app robotica seed   # competição de exemplo
curl localhost:8000/api/events
```

**Localmente** (com um MongoDB em `localhost:27017`):

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
flask --app robotica seed
flask --app robotica run
```

A conexão pode ser trocada com a variável `MONGO_URI`.

## Testes

```bash
pytest
```

São 25 testes com **pytest**, rodando contra um MongoDB de verdade (`TEST_MONGO_URI`, padrão `mongodb://localhost:27017`). Cada execução usa um banco próprio, apagado no final. Eles cobrem validação de peso por categoria, partidas entre categorias diferentes, tabela de pontos com desempate, empate total, ranking por tempo ignorando voltas inválidas e estatísticas de carreira.

No GitHub Actions, o CI roda lint e formatação (ruff), os testes contra um MongoDB 8.0 e o build da imagem Docker.

---

<details>
<summary>English</summary>

### Robotics Competition API

A **Flask + MongoDB** API to run robotics competitions: robots by weight class, sumo matches, line-follower time trials and **rankings computed with MongoDB aggregation pipelines** (`$unwind`, `$group`, `$lookup`, `$setWindowFields`).

- Sumo: 3 points per win, 1 per draw, tie-break by round difference then wins; full ties share the position
- Line follower: best valid lap counts (off-track runs are ignored)
- Career stats per robot, Pydantic validation, JSON errors, CORS for the web dashboard
- 25 pytest tests against a real MongoDB 8.0 in GitHub Actions, plus ruff and a Docker build

Run with `docker compose up --build -d` and load sample data with `docker compose exec api flask --app robotica seed`.

</details>
