import json
import yaml
from datetime import date

def gerar_arquivos_simulacao():
    """
    Gera os três arquivos de configuração (solo, manejo e cultura)
    para uma simulação de soja.
    """
    print("Gerando arquivos de configuração...")

    # --- 1. Arquivo de Solo: soil_file.json ---
    # Parâmetros representativos de um Latossolo Vermelho (Oxisol) do Cerrado,
    # com textura argilosa, boa profundidade e bem drenado.
    soil_params = {
        "SMW": 0.18,      # Ponto de Murcha Permanente
        "SMFCF": 0.36,    # Capacidade de Campo
        "SM0": 0.48,      # Saturação
        "CRAIRC": 0.10,   # Capacidade de Aeração Crítica
        "SOPE": 10.0,     # Profundidade máxima de evaporação do solo (cm)
        "KSUB": 0.5,      # Condutividade hidráulica do subsolo (cm/dia)
        "RDMSOL": 150.0   # Profundidade máxima de enraizamento permitida pelo solo (cm)
    }
    with open('soil_file.json', 'w') as f:
        json.dump(soil_params, f, indent=4)
    print("-> 'soil_file.json' criado com sucesso.")


    # --- 2. Arquivo de Manejo: agro_file.yaml ---
    # Define o cronograma da cultura conforme solicitado.
    # Nota: O período de 01/Jan a 28/Fev é muito curto para um ciclo completo
    # de soja (que geralmente leva de 100 a 140 dias). A simulação
    # terminará na data final, provavelmente antes da maturidade completa.
    agro_management = [
        {'CampaignStartTime': date(2024, 1, 1)},
        {'CropCalendar': {
            'crop_name': 'soybean',
            'variety_name': 'soybean_tropical_generic',
            'crop_start_date': date(2024, 1, 1),
            'crop_start_type': 'sowing',
            'crop_end_date': date(2024, 2, 28),
            'crop_end_type': 'harvest',
            'max_duration': 150
        }},
        {'StateEvents': None},
        {'TimedEvents': None}
    ]
    with open('agro_file.yaml', 'w') as f:
        yaml.dump(agro_management, f, default_flow_style=False, sort_keys=False)
    print("-> 'agro_file.yaml' criado com sucesso.")


    # --- 3. Arquivo da Cultura: crop_file.cab ---
    # Parâmetros para uma variedade de soja genérica adaptada a condições tropicais.
    # Baseado em parâmetros padrão do WOFOST para soja.
    crop_data = """
* ---------------------------------------------------------------------------
* CROP DATA FILE for WOFOST
*
* CROP: Soybean, generic tropical variety
* ---------------------------------------------------------------------------
* CROP DEVELOPMENT PARAMETERS
* Development depends on temperature and day length
TSUM1 =  750.0   * Temperature sum from emergence to anthesis (flowering) [degC.d]
TSUM2 = 1050.0   * Temperature sum from anthesis to maturity [degC.d]
IDSL = 0         * Indicator for developmental stage (0=summation of temp, 1=vernalization)
DTSMTB = 0.00,  0.00, \
         30.00, 30.00, \
         45.00, 45.00  * Daily temperature sum table for development rate calc.

* Day length sensitivity
DayLP = 12.5, 1.0, \
        12.5, 1.0     * Day length parameters for phenology correction
DVSI = 0.        * Initial development stage
DVSEND = 2.0     * Development stage at which simulation ends

* ---------------------------------------------------------------------------
* CO2 & PHOTOSYNTHESIS PARAMETERS
* Photosynthesis parameters for a C3 crop
CO2REF = 360.
CO2TR = 550.
CO2AM = 1110.
EFF = 0.45       * Light use efficiency for single leaves [kg CO2/ha/h / (J/m2/s)]
AMAXTB = 0.0, 35.0, \
         1.0, 35.0, \
         1.5, 35.0, \
         2.0, 35.0   * Max assimilation rate vs development stage
TMPFTB = 0, 0.0, 15, 1.0, 25, 1.0, 40, 0.0 * Temperature correction factor for AMAX

* ---------------------------------------------------------------------------
* PARTITIONING & LEAF PARAMETERS
* Allocation of assimilates to different organs
SLATB = 0.0, 0.0018, \
        0.5, 0.0020, \
        1.0, 0.0015, \
        2.0, 0.0010 * Specific leaf area vs development stage [ha/kg]
SPA = 0.00      * Specific pod area [ha/kg]
SSATB = 0.0, 0.0, 2.0, 0.0 * Specific stem area vs development stage [ha/kg]
KDIF = 0.60     * Extinction coefficient for diffuse visible light
RGRLAI = 0.012  * Maximum relative increase in LAI [ha/ha/d]

* Partitioning tables
FRTB = 0.0, 0.60, \
       1.0, 0.40, \
       1.2, 0.00, \
       2.0, 0.00 * Fraction of assimilates to roots vs DVS
FLTB = 0.0, 0.80, \
       0.8, 0.80, \
       1.0, 0.10, \
       1.3, 0.00, \
       2.0, 0.00 * Fraction of assimilates to leaves vs DVS
FSTB = 0.0, 0.20, \
       0.8, 0.20, \
       1.0, 0.90, \
       1.3, 0.00, \
       2.0, 0.00 * Fraction of assimilates to stems vs DVS
FOTB = 0.0, 0.00, \
       1.0, 0.00, \
       1.1, 1.00, \
       2.0, 1.00 * Fraction of assimilates to storage organs (beans) vs DVS

* ---------------------------------------------------------------------------
* ROOTING PARAMETERS
* Root growth and distribution
RDI = 10.0      * Initial rooting depth [cm]
RRI = 1.2       * Maximum daily increase of rooting depth [cm/d]
RDMCR = 120.0   * Maximum rooting depth in this crop [cm]

* ---------------------------------------------------------------------------
* INITIAL BIOMASS
TDWI = 20.      * Initial total dry weight of the crop [kg/ha]

* ---------------------------------------------------------------------------
* WATER USE PARAMETERS
* Parameters related to transpiration
CFET = 1.0      * Crop factor for potential evapotranspiration
DEPNR = 3.0     * Depletion number for transpiration reduction
"""
    with open('crop_file.cab', 'w') as f:
        f.write(crop_data)
    print("-> 'crop_file.cab' criado com sucesso.")
    print("\nTodos os arquivos foram gerados.")

if __name__ == '__main__':
    gerar_arquivos_simulacao()