#!/usr/bin/env python

"""
Weather extraction with meteostat by location lat and lon

- author: Daniele Salvatore Schiera
- maintainer: Daniele Salvatore Schiera
- email: daniele.schiera@polito.it
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from geopy.geocoders import Nominatim
from meteostat import Stations, Hourly
from meteostat.series.interpolate import interpolate

import logging

logging.basicConfig(filename='weatherlog.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(stream_handler)


# Column	Description	Type
# station	The Meteostat ID of the weather station (only if query refers to multiple stations)	String
# time	    The datetime of the observation	Datetime64
# temp	    The air temperature in °C	Float64
# dwpt	    The dew point in °C	Float64
# rhum	    The relative humidity in percent (%)	Float64
# prcp	    The one hour precipitation total in mm	Float64
# snow	    The snow depth in mm	Float64
# wdir	    The average wind direction in degrees (°)	Float64
# wspd	    The average wind speed in km/h	Float64
# wpgt	    The peak wind gust in km/h	Float64
# pres	    The average sea-level air pressure in hPa	Float64
# tsun	    The one hour sunshine total in minutes (m)	Float64
# coco	    The weather condition code	Float64

# Code	Weather Condition
# 1	    Clear
# 2	    Fair
# 3	    Cloudy
# 4	    Overcast
# 5	    Fog
# 6	    Freezing Fog
# 7	    Light Rain
# 8	    Rain
# 9	    Heavy Rain
# 10	Freezing Rain
# 11	Heavy Freezing Rain
# 12	Sleet
# 13	Heavy Sleet
# 14	Light Snowfall
# 15	Snowfall
# 16	Heavy Snowfall
# 17	Rain Shower
# 18	Heavy Rain Shower
# 19	Sleet Shower
# 20	Heavy Sleet Shower
# 21	Snow Shower
# 22	Heavy Snow Shower
# 23	Lightning
# 24	Hail
# 25	Thunderstorm
# 26	Heavy Thunderstorm
# 27	Storm

def get_weather_meteostat(city, year=2021, save_meteo=True, only_T=False, interpolation_limit=3):
    geolocator = Nominatim(user_agent="MyApp")
    location = geolocator.geocode({'city': city})
    if location == None:
        raise Exception(f"The location {city} does not exist")
    Lat = location.latitude
    Lon = location.longitude

    stations = Stations()
    stations = stations.nearby(Lat, Lon)
    station = stations.fetch(1)
    # Hourly data
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31, 23, 59)
    # Get hourly data
    meteo = Hourly(station.index.values[0], start, end, timezone='Europe/Rome')

    coverage = meteo.coverage('temp')
    meteo = meteo.normalize()
    interpolation_bool = False
    partial_bool = False
    if coverage < 1:
        logging.info(
            f"Note: The weather dataset is not complete for {city} in {year} due to gaps. The gaps will be filled by interpolation (max consecutive NaN {interpolation_limit}).")
        meteo = interpolate(meteo, limit=interpolation_limit)
        interpolation_bool = True

        coverage = meteo.coverage('temp')
        if coverage < 1:
            logging.info("Dateset interpolated but contains NaN yet. Increase limits or check validity of the data.")
            partial_bool = True

    meteo = meteo.fetch()

    if only_T:
        meteo = meteo.temp
        meteo = meteo.to_frame()

    meteo_filename = f"we_meteostat_id{station.index.values[0]}_{city}_{year}"
    if interpolation_bool:
        meteo_filename = meteo_filename + '_intrpl'
    if partial_bool:
        meteo_filename = meteo_filename + '_part'

    if save_meteo:
        meteo.to_csv(meteo_filename + '.csv')

    return meteo


def get_temperature_cities(cities, start, end, save=False):
    date_index = pd.date_range(start=pd.to_datetime(str(start)),
                               end=pd.to_datetime(str(end + 1)), freq='H',
                               tz='Europe/Rome', inclusive='left')

    wea = pd.DataFrame(index=date_index, columns=cities, dtype='float')
    for city in cities:
        flag = False
        for year in range(start, end + 1):
            if flag:
                weather = pd.concat([weather, get_weather_meteostat(city, year=year, save_meteo=save, only_T=True)])
            else:
                weather = get_weather_meteostat(city, year=year, save_meteo=save, only_T=True)
                flag = True
        wea[city] = weather
    return wea


if __name__ == "__main__":

    city = 'Torino'
    year = 2021

    wea = get_weather_meteostat(city, year=year, save_meteo=True, only_T=True, interpolation_limit=3)
    wea_temp_yearlystats = wea.groupby(pd.Grouper(freq='Y')).describe()
    wea_temp_yearlystats.to_csv('cities_temp_yearlystats' + '.csv')
    wea_temp_dailystats = wea.groupby(pd.Grouper(freq='D')).describe()
    wea_temp_dailystats.index = pd.MultiIndex.from_arrays(
        [wea_temp_dailystats.index.year, wea_temp_dailystats.index.month,wea_temp_dailystats.index.day], names=['Year', 'Month','Day'])
    wea_temp_dailystats.to_csv('cities_temp_dailystats' + '.csv')


