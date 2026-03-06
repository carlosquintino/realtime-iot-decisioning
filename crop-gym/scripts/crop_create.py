from pcse_gym.envs.common_env import PCSEEnv
import yaml
from datetime import  timedelta,date
import requests
import math
import openpyxl
from pcse.fileinput import ExcelWeatherDataProvider


class CreateCrop(PCSEEnv):

    def __init__(self,
                    latitude:float,
                    longitude:float,
                    *args,
                    **kwargs
                    ):

        self.latitude = latitude
        self.longitude = longitude
        self.args = args
        self.kwargs = kwargs
        self.get_range_date()

        self._fetch_enriched_weather()

        location=(latitude,longitude)
        
        super().__init__(location=location,*args,**kwargs)
        
        self.crop_data = []
        self.days_gone = 0

        

    
    def aply_action(self,action:dict):

        """
            This function is used to **apply a management action** to a **crop** and run 1 day in simulation.

            **Parameter**: 
            The `action` parameter must be a dictionary with the following keys:
            * **'irrigation'**: The **amount of water** to be irrigated, in **millimeters (mm)**.
            * **'N'**: The **amount of nitrogen (N) fertilizer** to be applied (the unit, e.g., kg/ha, should be specified, but is represented by the number).

            **Example of the 'action' dictionary**:
            action = {
                'irrigation': 0,
                'N': 10,
            }
        """

        prev_obs = self.crop_data[-1]["obs"] if self.crop_data else None

        obs, reward, done, truncated, info = self.step(action)

        self.crop_data.append(
            {
            "prev_obs": prev_obs,
            "obs":obs,
            "reward":reward,
            "done":done,
            "truncated":truncated,
            "info":info,
            "days_gone":self.days_gone,
            "action":action}
        )

        self.days_gone += 1


    def _fetch_enriched_weather(self):
        """
        Busca dados climáticos da API Open-Meteo e os formata corretamente para o PCSE.
        """
        print(f"Buscando dados da Open-Meteo para Lat={self.latitude}, Lon={self.longitude}")
        base_url = "https://archive-api.open-meteo.com/v1/archive"
        
        params_pcse = {
            "latitude": self.latitude, "longitude": self.longitude,
            "start_date": self.crop_start_date.strftime("%Y-%m-%d"), "end_date": self.crop_end_date.strftime("%Y-%m-%d"),
            "daily": [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "relative_humidity_2m_mean", "wind_speed_10m_max", "shortwave_radiation_sum"
            ],
            "timezone": "auto", "wind_speed_unit": "ms", "precipitation_unit": "mm"
        }
        
        try:
            print("Executando chamada à API Open-Meteo...")
            response_pcse = requests.get(base_url, params=params_pcse)
            response_pcse.raise_for_status()
            data_pcse = response_pcse.json()

        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar dados da Open-Meteo: {e}")
            raise

        # --- Armazenar Elevação e Processar Dados ---
        self.elevation = data_pcse.get('elevation', 0.0) # Armazena a elevação
        print(f"Elevação do local: {self.elevation}m")
        
        daily_data = data_pcse['daily']
        time_list = daily_data['time']
        
        self.enriched_weather_data = []
        
        for i, day_str in enumerate(time_list):
            try:
                day = date.fromisoformat(day_str)
                tmin = float(daily_data['temperature_2m_min'][i])
                tmax = float(daily_data['temperature_2m_max'][i])
                rh = float(daily_data['relative_humidity_2m_mean'][i])
                
                # Cálculo da pressão de vapor (VAP) em kPa, como esperado pelo PCSE
                es_tmin = 0.6108 * math.exp((17.27 * tmin) / (tmin + 237.3))
                es_tmax = 0.6108 * math.exp((17.27 * tmax) / (tmax + 237.3))
                es_avg = (es_tmin + es_tmax) / 2.0
                vap = (rh / 100.0) * es_avg

                # Converter radiação de J/m2 para kJ/m2
                irrad_kj = float(daily_data['shortwave_radiation_sum'][i]) / 1000.0
                
                row = [
                    day ,irrad_kj, tmin, tmax,
                    vap,float(daily_data['wind_speed_10m_max'][i]),
                    float(daily_data['precipitation_sum'][i]), -999
                    ]
                self.enriched_weather_data.append(row)
            
                
                
            except (ValueError, TypeError, KeyError) as e:
                print(f"Aviso: Dados inválidos ou ausentes para o dia {day_str}. Pulando. Erro: {e}")
                continue
        INPUT_PATH = 'weather/dummy_file.xlsx'
        OUTPUT_PATH = 'weather/data_weather.xlsx'

        START_LINE = 13
        
        wb = openpyxl.load_workbook(INPUT_PATH)
        ws = wb.active

        ws.cell(row=9, column=1, value=self.longitude)
        ws.cell(row=9, column=2, value=self.latitude)
        ws.cell(row=9, column=3, value=self.elevation)

        if not self.enriched_weather_data:
            raise ValueError("Nenhum dado climático válido foi processado da Open-Meteo.")
        
        for i, data in enumerate(self.enriched_weather_data, start=START_LINE):
            for j, value in enumerate(data, start=1):
                ws.cell(row=i, column=j, value=value)
                # cell = ws.cell(row=i, column=j, value=value)
                # if j == 1 and isinstance(value, (date, datetime)):
                #     cell.number_format = numbers.FORMAT_DATE_MMDDYYYY
        wb.save(OUTPUT_PATH)


    def convert_yml_file(self,file_name):

        with open(file_name) as file:
            f = yaml.safe_load(file)[0]
        
        return f


    def get_range_date(self):
        
        agro_file = self.kwargs.get('agro_config')
        
        f = self.convert_yml_file(agro_file)
        
        self.crop_start_date = f[list(f.keys())[0]]['CropCalendar']['crop_start_date']
        self.crop_end_date = f[list(f.keys())[0]]['CropCalendar']['crop_end_date']
        
        print(f[list(f.keys())[0]]['CropCalendar'])
    

    def current_day(self):

        return self.crop_start_date + timedelta(days=days_gone)
    
