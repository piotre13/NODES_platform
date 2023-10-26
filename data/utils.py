import pandas as pd

epw_col_names =['Year',
               'Month',
               'Day',
               'Hour',
               'Minute',
               'Data Source and Uncertainty Flags',
               'DryBulb',
               'DewPoint',
               'RelHum',
               'Atmos_Pressure',
               'ExtHorizRad',
               'ExtDirRad',
               'HorzIRSky',
               'GloHorzRad',
               'DirNorRad',
               'DifHorzRad',
               'GloHorzIllum',
               'DirNormIllum',
               'DifHorzIllum',
               'ZenLum',
               'WindDir',
               'WindSpd',
               'TotSkyCvr',
               'OpaqSkyCvr',
               'Visibility',
               'Ceiling_Hgt',
               'PresWeathObs',
               'PresWeathCodes',
               'Precip_Wtr',
               'Aerosol_Opt_Depth',
               'SnowDepth',
               'Days_Last_Snow',
               'Albedo',
               'Rain',
               'Rain_Quantity']

def convert_epw_to_csv(epw_file_path, csv_file_path):
    # Read the EPW file into a DataFrame
    data = pd.read_csv(epw_file_path, skiprows= 8 , header=None, names=epw_col_names)
    data.insert(0, 'DateTime', pd.to_datetime(data[['Year', 'Month', 'Day','Hour','Minute']]))
    data= data.drop(columns=['Year', 'Month', 'Day','Hour','Minute', 'Data Source and Uncertainty Flags'])
    print(data)
    data.to_csv(csv_file_path, index=False)


    # Remove the header row and reset the column names


if __name__ == '__main__':
    epw_file = 'meteo_file/meteo_bousson.epw'
    out_file = 'meteo_file/meteo_bousson.csv'
    convert_epw_to_csv(epw_file,out_file)