"""Saída estruturada da decisão (Pydantic).

Força o crew a produzir algo persistível/consultável — sem texto livre.
"""

from pydantic import BaseModel, Field


class FarmDecision(BaseModel):
    """Decisão consolidada de manejo para um dia/fazenda."""

    irrigate: bool = Field(description="Se deve irrigar agora.")
    irrigation_mm: float = Field(
        default=0.0, description="Lâmina de irrigação recomendada em mm (0 se não irrigar)."
    )
    apply_nitrogen: bool = Field(description="Se deve aplicar nitrogênio agora.")
    nitrogen_kg: float = Field(
        default=0.0, description="Quantidade de N recomendada em kg/ha (0 se não aplicar)."
    )
    rationale: str = Field(description="Justificativa curta da decisão (irrigação + N).")
    weather_summary: str = Field(description="Resumo da previsão do tempo usado na decisão.")
