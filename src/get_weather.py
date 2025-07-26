import requests


class Weather():

    def __init__(self,city=None):
        
        self.city = city

        if not city: self.get_city()
    
    #if not defined a city, use de current city from ip computer
    def get_city(self):
        ip = requests.get('https://api.ipify.org').text
        response = requests.get(f'http://ip-api.com/json/{ip}')
        data = response.json()
        self.city = data['city']


    #Return a weather forcast to the current city
    def get_weather_forecast(self) -> dict:
    
        url = f"https://wttr.in/{self.city}?format=j1"
        request = requests.get(url)

        return request.json()


# class WeatherForecastTool(BaseTool):
#     name: str = "Get Weather Forecast"
#     description: str = (
#         "Useful for getting the current 3-day weather forecast in JSON format "
#         "for the current location (determined by IP). "
#         "Returns detailed weather data including temperature, conditions, and precipitation."
#     )
#     def _run(self, city: str = None) -> dict:
#         """
#         Executes the weather forecast retrieval.
#         The 'city' argument is optional for this tool as it uses the current city.
#         """
#         weather = Weather()

#         return weather.get_weather_forecast()        