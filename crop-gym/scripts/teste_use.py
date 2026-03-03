from crop_create import CreateCrop

from pcse.fileinput import CABOFileReader, YAMLCropDataProvider
from pcse.util import WOFOST80SiteDataProvider

env = CreateCrop(
    model_config='Wofost80_NWLP_FD.conf',
    agro_config='/home/ubuntu/pgc/realtime-iot-decisioning/crop-gym/PCSE-Gym/pcse_gym/envs/configs/agro/potato_cropcalendar.yaml',
    crop_parameters=YAMLCropDataProvider(force_reload=True),
    site_parameters=WOFOST80SiteDataProvider(WAV=10,  # Initial amount of water in total soil profile [cm]
                                             NAVAILI=10,  # Amount of N available in the pool at initialization of the system [kg/ha]
                                             PAVAILI=50,  # Amount of P available in the pool at initialization of the system [kg/ha]
                                             KAVAILI=100,  # Amount of K available in the pool at initialization of the system [kg/ha]
                                             ),
    soil_parameters=CABOFileReader('/home/ubuntu/pgc/realtime-iot-decisioning/crop-gym/PCSE-Gym/pcse_gym/envs/configs/soil/ec3.CAB'),
)

a1 = action = {
                'irrigation': 0,
                'N': 0,
            }

a2 = action = {
                'irrigation': 0,
                'N': 0,
            }

print(env.get_current_weather())
env.aply_action(action=a1)


# Exemplo: comparar soil water antes/depois
# before = env.crop_data[-1]["prev_obs"]
# after  = env.crop_data[-1]["obs"]


# env.aply_action(action=a2)

# before = env.crop_data[-1]["prev_obs"]
# after  = env.crop_data[-1]["obs"]

# print(before,after)