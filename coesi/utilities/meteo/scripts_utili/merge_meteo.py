import pandas as pd

df=pd.read_csv('IPIEMONT220.csv', index_col='DateUTC')
df.index=pd.to_datetime(df.index).tz_localize('UTC')
df=df.resample('15T').mean().interpolate()
df=df.drop(['Conditions', 'Clouds'],axis=1)
df1=pd.read_csv('clean_dataset.csv', index_col='Timestamp')
df1.index=pd.to_datetime(df1.index).tz_localize('UTC')
df.columns=['temperature','dewPoint','pressure','windBearing','windSpeed','WindSpeedGustKMH','humidity','precipIntensity','dailyrainMM','GHI',]
df2=df1.append(df)
df2=df2.drop(['GHI_cs', 'K', 'WindSpeedGustKMH', 'cloudCover', 'day','hour', 'minute','sunriseTime', 'sunsetTime',
       'sunshineDuration','uvIndex','precipProbability','dailyrainMM'],axis=1)
df2.columns=['ghi', 'T_dewPoint', 'humidity', 'precipIntensity',
       'pressure', 'T_ext', 'windBearing', 'windSpeed']
df2.index.name='Timestamp'
df2.to_csv('meteo_2010_2018_UTC.csv')
rad=pd.DataFrame(df2.ghi)
rad.to_csv('solar_rad_UTC.csv')
