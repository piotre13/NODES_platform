import pandas as pd


"""Prepare csv extracted from energyplus epw to csv to be ready as csv for mosaik"""

#path_filemeteo = r"D:\Projects\PycharmProjects\casestudy\uesa\resources\weather_data\USA_CA_San.Francisco.Intl.AP.724940_TMY3EPW.csv"
path_filemeteo = r"C:\Users\Mocci\PycharmProjects\uesa\uesapp\resources\weather_data\ITA_Torino-CaselleEPW.csv"
df = pd.read_csv(path_filemeteo,
    sep=",",
    header=17,encoding= 'unicode_escape' )

name_meteo = path_filemeteo.split("\\")[-1].split(".csv")[0]
df = df.drop(0).reset_index(drop=True)
df = df.drop(columns="Datasource")

col_ori = df.columns
col_new = [names.split(" {")[0].replace(" ", "_") for names in col_ori]
columns_name_maps = dict(zip(col_ori, col_new))

df.rename(columns=columns_name_maps, inplace=True)


def custom_to_datetime(date):
    # If the time is 24, set it to 0 and increment day by 1
    if date.split(" ")[1][0:2] == '24':
        return pd.to_datetime(date[:-6], format='%Y/%m/%d') + pd.Timedelta(days=1)
    else:
        return pd.to_datetime(date, format='%Y/%m/%d %H:%M:%S')


df.insert(0, 'DateTime', df['Date'] + ' ' + df['HH:MM'])

df['DateTime'] = df['DateTime'].apply(custom_to_datetime)

df.drop(columns=["Date", 'HH:MM'], inplace=True)


# add time 0 as equal to time 1
df.loc[-1] = df.loc[0]
df.index = df.index + 1  # shifting index
df = df.sort_index() # sort
df.loc[0, 'DateTime'] = df.loc[0, 'DateTime'] + pd.Timedelta(seconds=-3600) # set to 00.00.00


# set the reference year
year = 2015
df['DateTime'] = df.DateTime.map(lambda t: t.replace(year=year))
# drop last value to mantain 8750 value per year
df.drop(labels=8760, axis=0, inplace=True)



df.to_csv(fr"C:\Users\Mocci\PycharmProjects\uesa\models\timeseries\{name_meteo}.csv", index=False)

# %%

df_mk = pd.read_csv(fr"C:\Users\Mocci\PycharmProjects\uesa\models\timeseries\{name_meteo}.csv")
df_mk.DateTime = pd.to_datetime(df_mk.DateTime)
df_mk.set_index(pd.DatetimeIndex(df_mk.DateTime), inplace=True)
df_mk.drop(columns='DateTime', inplace=True)