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

# crew = Crew(
#     agents=[weather_analyst],
#     tasks=[weather_summary_task],
#     verbose=True
# )

# result = crew.kickoff()
# print(result)

# make_decision()