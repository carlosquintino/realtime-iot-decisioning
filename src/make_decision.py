from datetime import datetime
from crewai import Agent, Task, Crew, Process
from get_weather import Weather
from llm_connection import Llm_connection


connection = Llm_connection()
model = connection.connection()

def make_decision():
    
    llm = connection.connection()
    weather_analyst = Agent(
        role='Weather Data Analyst',
        goal=f'Summarize critical rain forecast information from JSON data, focusing on probability, {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, precipitation amount if it rains, and other key details.',
        backstory="""You are a meticulous meteorology expert with a strong analytical mind. 
        Your primary function is to interpret complex weather data, especially JSON outputs from weather APIs. 
        You excel at extracting the most relevant information for decision-making, such as agricultural planning or event management. 
        You ensure that only essential details, specifically related to rain probability, timing, and intensity, are highlighted clearly and concisely.""",
        verbose=True,
        allow_delegation=False
    )
    weather = Weather()
    weather_summary_task = Task(
        description=(
            f"Analyze the following JSON weather data to extract and summarize "
            f"the most important rain forecast details. "
            f"Specifically, identify the 'probability of rain', 'current date and time' "
            f"of the forecast, the 'expected precipitation amount if it rains', "
            f"and any 'other critical points' related to rainfall. "
            f"Present this summary in a clear, concise format, in English.\n\n"
            f"**Weather Data:**\n```json\n{weather.get_weather_forecast()}\n```"
        ),
        expected_output="A summarized report in English, detailing rain probability, forecast date/time, expected precipitation, and any other critical rain-related information. Example: 'Rain Probability: 70%. Forecast for July 26, 2025, 1:00 AM. Expected Precipitation: 5mm. Key points: Light showers anticipated from 2 AM to 4 AM.'",
        agent=weather_analyst,
    )

    crew = Crew(
        agents=[weather_analyst],
        tasks=[weather_summary_task],
        verbose=True
    )

    result = crew.kickoff()
    print(result)

make_decision()