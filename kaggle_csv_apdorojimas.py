import pandas as pd

DATA_DIR = 'solar_kaggle'

# 1. Įkelti abiejų elektrinių duomenis
gen_1 = pd.read_csv(f'{DATA_DIR}/Plant_1_Generation_Data.csv')
weather_1 = pd.read_csv(f'{DATA_DIR}/Plant_1_Weather_Sensor_Data.csv')
gen_2 = pd.read_csv(f'{DATA_DIR}/Plant_2_Generation_Data.csv')
weather_2 = pd.read_csv(f'{DATA_DIR}/Plant_2_Weather_Sensor_Data.csv')

# 2. Suvienodinti datos formatą
# SVARBU: šiame duomenų rinkinyje datos formatas skiriasi NE TIK tarp generation/weather,
# bet ir tarp pačių generation failų:
#   Plant_1_Generation_Data.csv:  '15-05-2020 00:00'    (DD-MM-YYYY)
#   Plant_2_Generation_Data.csv:  '2020-05-15 00:00:00' (YYYY-MM-DD, kaip weather failuose)
gen_1['DATE_TIME'] = pd.to_datetime(gen_1['DATE_TIME'], format='%d-%m-%Y %H:%M')
gen_2['DATE_TIME'] = pd.to_datetime(gen_2['DATE_TIME'])

# Weather: '2020-05-15 00:00:00' (YYYY-MM-DD) - abiejuose failuose vienodas formatas
weather_1['DATE_TIME'] = pd.to_datetime(weather_1['DATE_TIME'])
weather_2['DATE_TIME'] = pd.to_datetime(weather_2['DATE_TIME'])


def process_plant(gen: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Sugrupuoja generation duomenis pagal laiką (susumuoja visus inverterius)
    ir sujungia su weather duomenimis tai pačiai elektrinei."""
    gen_grouped = gen.groupby('DATE_TIME').agg({
        'DC_POWER': 'sum',
        'AC_POWER': 'sum'
    }).reset_index()
    return pd.merge(gen_grouped, weather, on='DATE_TIME', how='inner')


# 3. Apdoroti abi elektrines atskirai (kad nesusimaišytų PLANT_ID) ir sujungti
merged_1 = process_plant(gen_1, weather_1)
merged_2 = process_plant(gen_2, weather_2)
merged = pd.concat([merged_1, merged_2], ignore_index=True)

# 4. Papildomas požymis: radiacijos ir temperatūros sąveika.
# Fizikinis pagrindas: panelio efektyvumas mažėja įkaitus (~-0,4%/°C silicio paneliams),
# tad ta pati radiacija karštą dieną duoda mažiau galios nei vėsią - linijinė regresija be
# šio sąveikos nario negali išreikšti, kad radiacijos poveikis galiai priklauso nuo
# temperatūros (ji modeliuoja tik atskirą kiekvieno požymio poveikį).
# `hour`/`day_of_year` sąmoningai NEpridėti: radiacija jau pati savaime koduoja paros laiką
# (naktį = 0), o šis duomenų rinkinys apima tik ~34 dienas, tad tikro sezoniškumo jame nėra.
merged['IRRADIATION_X_TEMP'] = merged['IRRADIATION'] * merged['MODULE_TEMPERATURE']

# 5. Paruošti X ir y
X = merged[['AMBIENT_TEMPERATURE', 'MODULE_TEMPERATURE', 'IRRADIATION', 'IRRADIATION_X_TEMP']]
y = merged['AC_POWER']

print(f"Duomenų dydis: {merged.shape}")
print(f"Elektrinės: {sorted(merged['PLANT_ID'].unique())}")
print(f"Laikotarpis: nuo {merged['DATE_TIME'].min()} iki {merged['DATE_TIME'].max()}")
print(f"Vidutinė galia: {y.mean():.2f} W")

# 6. Išsaugoti apdorotus duomenis, kad modelio treniravimo skriptas galėtų juos
# tiesiog įkelti, o ne kaskart iš naujo apdoroti žalius CSV failus.
OUTPUT_PATH = 'data/kaggle_solar_merged.csv'
merged.to_csv(OUTPUT_PATH, index=False)
print(f"Apdoroti duomenys išsaugoti: {OUTPUT_PATH}")
