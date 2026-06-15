"""Crew CrewAI de decisão: clima + solo → irrigação + nitrogênio → decisão final.

Refatora o make_decision.py antigo:
  • adiciona o especialista em Nitrogênio (faltava);
  • encadeia as tasks via `context=` (o antigo passava o objeto Task, não o resultado);
  • força saída estruturada (output_pydantic=FarmDecision);
  • LLM trocável via src.llm.
"""

import json

from crewai import Agent, Crew, Process, Task

from ..llm import get_llm
from .schemas import FarmDecision


class DecisionCrew:
    """Monta e executa o crew para um snapshot de fazenda + previsão do tempo."""

    def __init__(self):
        self.llm = get_llm()

    # ── agentes ───────────────────────────────────────────────────────────────
    def _agents(self):
        weather = Agent(
            role="Weather Data Analyst",
            goal="Resumir o risco de chuva e condições relevantes a partir da previsão.",
            backstory="Meteorologista que extrai probabilidade de chuva, volume e timing "
                      "para apoiar decisões agrícolas.",
            llm=self.llm, verbose=True, allow_delegation=False,
        )
        soil = Agent(
            role="Field Sensor Snapshot Analyst",
            goal="Interpretar o snapshot de sensores (solo/cultura) sem tomar decisões.",
            backstory="Analista de campo que descreve umidade do solo (SM), estágio da "
                      "cultura (DVS), índice foliar (LAI) e nutrientes, de forma objetiva.",
            llm=self.llm, verbose=True, allow_delegation=False,
        )
        irrigation = Agent(
            role="Irrigation Strategy Specialist",
            goal="Decidir se irriga e quantos mm, sendo conservador com água.",
            backstory="Especialista em irrigação de precisão. Não irriga se chuva é "
                      "iminente ou se a umidade do solo já é suficiente.",
            llm=self.llm, verbose=True, allow_delegation=False,
        )
        nitrogen = Agent(
            role="Nitrogen Management Specialist",
            goal="Decidir se aplica nitrogênio e quantos kg/ha.",
            backstory="Agrônomo de nutrição. Usa N disponível (NAVAIL), índice de "
                      "nutrição (NNI), demanda (Ndemand) e estágio (DVS). Evita aplicar "
                      "perto da maturação ou quando o NNI já está adequado (~1.0).",
            llm=self.llm, verbose=True, allow_delegation=False,
        )
        synthesizer = Agent(
            role="Farm Decision Synthesizer",
            goal="Consolidar as recomendações numa decisão final estruturada.",
            backstory="Responsável por unir as análises de irrigação e nitrogênio numa "
                      "única decisão objetiva e acionável.",
            llm=self.llm, verbose=True, allow_delegation=False,
        )
        return weather, soil, irrigation, nitrogen, synthesizer

    # ── contexto da cultura ──────────────────────────────────────────────────────
    @staticmethod
    def _crop_context(farm_info: dict | None) -> str:
        """Bloco de contexto agronômico (cultura/variedade/local/safra) para os
        prompts. Vazio se não houver metadados da fazenda."""
        if not farm_info:
            return ""
        crop = farm_info.get("crop_name") or "cultura não especificada"
        parts = [f"Cultura: {crop}"]
        if farm_info.get("crop_variety"):
            parts.append(f"variedade {farm_info['crop_variety']}")
        line = ", ".join(parts) + "."
        extra = []
        if farm_info.get("location_name"):
            extra.append(f"Local: {farm_info['location_name']}")
        if farm_info.get("season_start"):
            extra.append(f"início da safra: {farm_info['season_start']}")
        if extra:
            line += " " + " | ".join(extra) + "."
        return (
            "CONTEXTO DA LAVOURA (use conhecimento agronômico ESPECÍFICO desta cultura — "
            "as janelas críticas de água e nitrogênio e a sensibilidade por estágio "
            "fenológico variam de espécie para espécie):\n"
            f"{line}\n\n"
        )

    # ── execução ────────────────────────────────────────────────────────────────
    def run(self, snapshot: dict, weather: dict, data_date: str,
            farm_info: dict | None = None) -> FarmDecision:
        weather_a, soil_a, irrig_a, n_a, synth_a = self._agents()
        snapshot_json = json.dumps(snapshot, ensure_ascii=False)
        weather_json = json.dumps(weather, ensure_ascii=False)
        crop_block = self._crop_context(farm_info)

        weather_task = Task(
            description=f"Analise a previsão do tempo (JSON) e resuma probabilidade de "
                        f"chuva, volume esperado e timing.\n\nPrevisão:\n```json\n{weather_json}\n```",
            expected_output="Resumo curto do risco de chuva (probabilidade, volume mm, quando).",
            agent=weather_a,
        )
        soil_task = Task(
            description=crop_block +
                        f"Interprete o snapshot de sensores do dia {data_date} (sem decidir). "
                        f"Contextualize os valores para esta cultura e estágio. "
                        f"Destaque SM (umidade), DVS (estágio), LAI, e nutrientes "
                        f"(NAVAIL, NNI, Ndemand, NPKI).\n\nSnapshot:\n```json\n{snapshot_json}\n```",
            expected_output="Resumo claro das condições de solo, estágio da cultura e nutrição.",
            agent=soil_a,
        )
        irrigation_task = Task(
            description=crop_block +
                        "Com base nos resumos de clima e solo, decida se a lavoura deve ser "
                        "irrigada agora e quantos mm, considerando a demanda hídrica típica "
                        "desta cultura no estágio atual. Seja conservador: não irrigue se há "
                        "chuva iminente ou umidade do solo suficiente.",
            expected_output="Decisão de irrigação: irrigar (sim/não), mm recomendados e justificativa.",
            agent=irrig_a,
            context=[weather_task, soil_task],
        )
        nitrogen_task = Task(
            description=crop_block +
                        "Com base no resumo de solo/nutrição, decida se deve aplicar nitrogênio "
                        "agora e quantos kg/ha, considerando a curva de absorção de N desta "
                        "cultura por estágio. Evite aplicar perto da maturação (DVS alto) ou "
                        "quando o NNI já está adequado.",
            expected_output="Decisão de nitrogênio: aplicar (sim/não), kg/ha e justificativa.",
            agent=n_a,
            context=[soil_task],
        )
        synth_task = Task(
            description="Consolide as decisões de irrigação e nitrogênio numa decisão final "
                        "estruturada, preenchendo todos os campos do schema.",
            expected_output="Objeto FarmDecision com irrigate, irrigation_mm, apply_nitrogen, "
                            "nitrogen_kg, rationale e weather_summary.",
            agent=synth_a,
            context=[weather_task, soil_task, irrigation_task, nitrogen_task],
            output_pydantic=FarmDecision,
        )

        crew = Crew(
            agents=[weather_a, soil_a, irrig_a, n_a, synth_a],
            tasks=[weather_task, soil_task, irrigation_task, nitrogen_task, synth_task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()
        decision = result.pydantic

        # Dump completo da decisão final estruturada (todos os campos do schema).
        print("\n" + "=" * 72)
        print(f"DECISÃO FINAL — {data_date}")
        print("=" * 72)
        print(json.dumps(decision.model_dump(), ensure_ascii=False, indent=2))
        print("=" * 72 + "\n", flush=True)

        return decision
