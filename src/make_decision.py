from datetime import datetime
from crewai import Agent, Task, Crew, Process
from get_weather import Weather
from llm_connection import Llm_connection


connection = Llm_connection()
connection.connection()

class MakeDecision():

    def __init__(self,sensor_data):
        self.weather = Weather()
        self.sensor_data = sensor_data

    def weather_analyst(self):
    
        self.weather_analyst = Agent(
            role='Weather Data Analyst',
            goal=f'Summarize critical rain forecast information from JSON data, focusing on probability, {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, precipitation amount if it rains, and other key details.',
            backstory="""You are a meticulous meteorology expert with a strong analytical mind. 
            Your primary function is to interpret complex weather data, especially JSON outputs from weather APIs. 
            You excel at extracting the most relevant information for decision-making, such as agricultural planning or event management. 
            You ensure that only essential details, specifically related to rain probability, timing, and intensity, are highlighted clearly and concisely.""",
            verbose=True,
            allow_delegation=False
        )

    def weather_task(self):
        self.weather_summary_task = Task(
        description=(
            f"Analyze the following JSON weather data to extract and summarize "
            f"the most important rain forecast details. "
            f"Specifically, identify the 'probability of rain', 'current date and time' "
            f"of the forecast, the 'expected precipitation amount if it rains', "
            f"and any 'other critical points' related to rainfall. "
            f"Present this summary in a clear, concise format, in English.\n\n"
            f"**Weather Data:**\n```json\n{self.weather.get_weather_forecast()}\n```"
        ),
        expected_output="A summarized report in English, detailing rain probability, forecast date/time, expected precipitation, and any other critical rain-related information. Example: 'Rain Probability: 70%. Forecast for July 26, 2025, 1:00 AM. Expected Precipitation: 5mm. Key points: Light showers anticipated from 2 AM to 4 AM.'",
        agent=self.weather_analyst,
    )

    def sensor_analyst(self):
         
         self.sensor_analyst = Agent(
            role='Field Sensor Snapshot Analyst',
            goal=f'Interpret the latest sensor snapshot from a plantation as of {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, extracting key information about soil conditions and crop-related context without making decisions.',
            backstory="""You are a highly focused field data analyst trained to work with isolated sensor snapshots from agricultural environments.
            Each snapshot represents the most recent condition of the plantation, including metrics like soil humidity, temperature, and possibly crop type.
            Your task is to summarize this current data clearly and objectively, without comparing it to previous values or making any recommendations.
            You support other agents by offering reliable and well-structured insights for further analysis and decision-making.""",
            verbose=True,
            allow_delegation=False
        )
    
    def sensor_task(self):
        self.sensor_snapshot_summary_task = Task(
            description=f"""Analyze a single snapshot of plantation sensor data (e.g., soil humidity, temperature, crop type).
            Extract and summarize the key environmental conditions.
            Avoid comparisons with past data or any decision-making.
            If crop type is present, provide context about the environment it’s experiencing.
            Here is the snapshot {self.sensor_data}""",
            expected_output="""A short and clear summary including:
            - Soil humidity value and interpretation (e.g., low/medium/high)
            - Temperature (if present)
            - Crop type (if present) and its current environmental context
            - Timestamp or reference to when the data was collected (if available)""",
            agent=self.sensor_analyst
        )
    
    def decision_agent(self):
        self.irrigation_decision_agent = Agent(
            role="Irrigation Strategy Specialist",
            goal=f"Make a data-driven irrigation decision based on current weather and plantation conditions as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.",
            backstory="""You are a domain expert in smart irrigation and precision agriculture.
            You are responsible for determining whether irrigation is necessary based on summarized weather forecasts and field sensor snapshots.
            You must reason using both weather risk factors (rain probability and intensity) and current soil conditions (humidity and temperature).
            Be conservative with water use — do not irrigate if rainfall is imminent or humidity is already sufficient.""",
            verbose=True,
            allow_delegation=False
        )
    
    def decision_task(self):
        self.irrigation_decision_task = Task(
            description=(
                f"You are given two summaries:\n\n"
                f"1. **Weather Summary**:\n{self.weather_summary_task}\n\n"
                f"2. **Sensor Summary**:\n{self.sensor_snapshot_summary_task}\n\n"
                f"Based on this information, decide if the plantation **should be irrigated now**.\n"
                f"Consider the soil humidity (e.g., low/medium/high), forecasted rain (e.g., probability and intensity), and temperature (if relevant).\n\n"
                f"Respond with one of the following options:\n"
                f"- 'Irrigation Recommended: Yes.' with a short justification.\n"
                f"- 'Irrigation Recommended: No.' with a short justification.\n"
                f"Optionally, include 'Suggested Duration: X minutes' if irrigation is recommended."
            ),
            expected_output="A short and justified decision about irrigation, e.g.: 'Irrigation Recommended: No. Rain expected within 2 hours (80% probability). Humidity is medium.'",
            agent=self.irrigation_decision_agent
        )
    def run(self):
        # 1. Agentes
        self.weather_analyst()
        self.sensor_analyst()

        # 2. Tasks para agentes de clima e sensor
        self.weather_task()
        self.sensor_task()

        # 3. Executa crews separadamente para obter os resumos
        weather_summary = Crew(agents=[self.weather_analyst], tasks=[self.weather_summary_task], verbose=True).kickoff()
        sensor_summary = Crew(agents=[self.sensor_analyst], tasks=[self.sensor_snapshot_summary_task], verbose=True).kickoff()

        # 4. Agente e task de decisão (com os resumos como entrada)
        self.decision_agent()
        self.decision_task()

        # 5. Executa decisão
        final_decision = Crew(agents=[self.irrigation_decision_agent], tasks=[self.irrigation_decision_task], verbose=True).kickoff()

        print("🌱 Final Decision:\n", final_decision)
