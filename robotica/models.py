"""Categorias e modelos de entrada validados com Pydantic."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Modo "partidas": confronto direto, vitória vale 3 pontos e empate 1 (sumô).
# Modo "tempo": cada robô faz tomadas de tempo e vale a melhor (seguidor de linha).
CATEGORIES: dict[str, dict] = {
    "sumo_3kg": {"name": "Sumô 3 kg autônomo", "max_weight_g": 3000, "mode": "partidas"},
    "sumo_500g": {"name": "Mini sumô 500 g", "max_weight_g": 500, "mode": "partidas"},
    "sumo_100g": {"name": "Micro sumô 100 g", "max_weight_g": 100, "mode": "partidas"},
    "seguidor_de_linha": {"name": "Seguidor de linha", "max_weight_g": 1000, "mode": "tempo"},
}

Category = Literal["sumo_3kg", "sumo_500g", "sumo_100g", "seguidor_de_linha"]
Round = Literal["classificatoria", "oitavas", "quartas", "semifinal", "final"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RobotIn(StrictModel):
    name: str = Field(min_length=2, max_length=60)
    team: str = Field(min_length=2, max_length=60)
    category: Category
    weight_g: int = Field(gt=0)

    @model_validator(mode="after")
    def weight_within_category(self):
        limit = CATEGORIES[self.category]["max_weight_g"]
        if self.weight_g > limit:
            raise ValueError(f"Peso acima do limite da categoria ({limit} g).")
        return self


class RobotPatch(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=60)
    weight_g: int | None = Field(default=None, gt=0)


class EventIn(StrictModel):
    name: str = Field(min_length=3, max_length=100)
    city: str = Field(min_length=2, max_length=80)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def dates_in_order(self):
        if self.end_date < self.start_date:
            raise ValueError("A data final não pode ser anterior à inicial.")
        return self


class MatchIn(StrictModel):
    robot_a: str
    robot_b: str
    round: Round = "classificatoria"
    # Rounds vencidos por cada robô (sumô costuma ser melhor de 3)
    score_a: int = Field(ge=0, le=3)
    score_b: int = Field(ge=0, le=3)

    @model_validator(mode="after")
    def different_robots(self):
        if self.robot_a == self.robot_b:
            raise ValueError("Um robô não pode enfrentar ele mesmo.")
        return self


class RunIn(StrictModel):
    robot_id: str
    time_ms: int = Field(gt=0, le=600_000)
    valid: bool = True
