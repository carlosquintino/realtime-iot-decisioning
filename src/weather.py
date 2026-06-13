"""Previsão do tempo via wttr.in.

Substitui o get_weather.py: localização configurável por env (em container não dá
para deduzir cidade pelo IP). Retorna um resumo compacto para economizar tokens.
"""

import requests

from . import config


def get_weather_forecast(location: str | None = None) -> dict:
    """Retorna previsão compacta (próximos dias) para a localização configurada."""
    loc = location or config.WEATHER_LOCATION
    url = f"https://wttr.in/{loc}?format=j1"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    raw = resp.json()

    forecast = []
    for day in raw.get("weather", [])[:3]:
        hourly = day.get("hourly", [])
        chance_rain = max((int(h.get("chanceofrain", 0)) for h in hourly), default=0)
        precip = sum(float(h.get("precipMM", 0)) for h in hourly)
        forecast.append({
            "date": day.get("date"),
            "maxtempC": day.get("maxtempC"),
            "mintempC": day.get("mintempC"),
            "max_chance_of_rain_pct": chance_rain,
            "total_precip_mm": round(precip, 1),
        })

    current = (raw.get("current_condition") or [{}])[0]
    return {
        "location": loc,
        "current": {
            "temp_C": current.get("temp_C"),
            "humidity": current.get("humidity"),
            "precipMM": current.get("precipMM"),
        },
        "forecast": forecast,
    }
