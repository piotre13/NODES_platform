OneRoom_win_2_eplus_sim.idf
pure version of the one room with 2 windows used for simulation in E+
wth = ITA_PM_Torino.AF.160595_TMYx.epw OR my_epw_file

OneRoom_win_2_fmu_sim.idf
base idf used to convert in fmu.
fmu_sim has the following external interfaces activated:
- outputs Tamb and TRooMea
- inputs Q(initial 0) and Peo(initial 0)

OneRoom_win_2_fmu_sim_internal_epw.idf -> fmu
idf used to convert in fmu integrating also an epw file directly in the fmu
wth = ITA_PM_Torino.AF.160595_TMYx.epw or my_epw_file

OneRoom_win_2_fmu_sim_external_weather.idf -> fmu
idf used to convert in fmu and integrating external weather data
external interfaces activated:
- actuators Tbulb (initial 20), Tdew(initial 20), RH(50)
weather = my_epw_file (that is equal to the file given step by step, used to check)