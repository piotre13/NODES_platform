import pandas as pd
from coesi.utilities.meteo import dec
from coesi.utilities.epw.epw import epw
# TODO rivedere il funzionamento
start='2015-01-01 00:00:00'
end='2015-12-31 23:59:00'
epw_file= 'ITA_Torino.160590_IWEC.epw'
def main(start_date,end_date,epw_file):


	start_date=pd.to_datetime(start_date).tz_localize('UTC')
	end_date=pd.to_datetime(end_date).tz_localize('UTC')
	meteo=pd.read_csv('meteo_2010_2018_UTC.csv', index_col='Timestamp', parse_dates=[0, ])
	meteo=meteo.resample('H').mean().interpolate()
	meteo=meteo.loc[start_date:end_date]
	data=epw()
	data.read(epw_file)
	latitude=float(data.headers['LOCATION'][5])
	longitude=float(data.headers['LOCATION'][6])
	elevation=float(data.headers['LOCATION'][8])
	data.headers['LOCATION'][7]='0.0'
	rad=dec.main(pd.DataFrame(meteo.ghi),latitude,longitude,elevation)
	df=data.dataframe.copy()
	df['Dew Point Temperature']=meteo.T_dewPoint.values
	df['Dry Bulb Temperature']=meteo.T_ext.values
	df['Atmospheric Station Pressure']=100*meteo.pressure.values
	df['Relative Humidity']=meteo.humidity.values
	df['Global Horizontal Radiation']=rad.ghi.values
	df['Direct Normal Radiation']=rad.dni.values
	df['Diffuse Horizontal Radiation']=rad.dhi.values
	df['Wind Direction']=meteo.windBearing.values
	df['Wind Speed']=meteo.windSpeed.values
	df.Year=meteo.index.year
	df.Month=meteo.index.month
	df.Day=meteo.index.day
	data.dataframe=df.copy()
	data.write('my_epw_file.epw')


if __name__ == "__main__":
    main(start,end,epw_file)