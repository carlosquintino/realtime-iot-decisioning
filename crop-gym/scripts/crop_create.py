from pcse_gym.envs.common_env import PCSEEnv


class CreateCrop(PCSEEnv):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        self.crop_data = []
        self.days_gone = 1

    
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
        
    def get_current_weather(self):
        engine = self.unwrapped.simulator.engine
        
        # Pega os dados climáticos para a data atual da simulação
        current_date = engine.day
        weather_day = engine.weather_provider(current_date)
        
        # Pega variáveis de solo e cultura
        # 'SM' = Soil Moisture, 'LAI' = Leaf Area Index
        soil_moisture = engine.get_variable('SM')
        
        r =  {
            "date": current_date,
            "temp_min": weather_day.TMIN,
            "temp_max": weather_day.TMAX,
            "rain": weather_day.RAIN,
            "irrad": weather_day.IRRAD,
            "soil_moisture": soil_moisture
        }

        print(r)
