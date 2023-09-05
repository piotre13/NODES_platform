##########################################################################################
#   Script for the Download of historic data of weatherstation from Weatherundergound    #
#  The request info are the ID of the Station and the start and end date of the series   #
#	Developed by Lorenzo Bottaccioli	for info lorenzo.bottaccioli@polito.it   #
##########################################################################################

import datetime, datetime
import urllib
import os
import sys
import requests
from optparse import OptionParser

    
start='2015-12-30'
end='2018-12-31'
station_id="IPIEMONT220"

def write_function(x,f):
    stringa=x.decode()
    stringa=stringa.replace('<br>','')
    if(stringa[0:]!=('\n')):
        f.write(stringa[0:])
    return stringa

def main(station_id,start,end):
    start_date=datetime.datetime.strptime(start,'%Y-%m-%d')
    end_date= datetime.datetime.strptime(end,'%Y-%m-%d')
    f=open(station_id+'.csv', mode='w')
    ffcheck=True
    delta = datetime.timedelta(days=1)
    count=start_date


    url = "https://www.wunderground.com/weatherstation/WXDailyHistory.asp"



    headers = {
        'cache-control': "no-cache",
        'postman-token': "72eed757-662e-d840-6ec2-4c0da5caaff9"
        }


    while count <= end_date:
           d=count.day
           m=count.month
           y=count.year
           count+=delta
           #url = 'http://www.wunderground.com/weatherstation/WXDailyHistory.asp?ID='+str(station_id)+'&day='+str(d)+'&month='+str(m)+'&year='+str(y)+'graphspan=day&format=1'
           querystring = {"ID":station_id,"day":str(d),"month":str(m),"year":str(y)+"graphspan=day","format":"1"}
           print (station_id,y,m,d)
           response = requests.request("GET", url, headers=headers, params=querystring)
           fcheck=0
           for x in response.iter_lines():
                    if (fcheck<2):
                        if(ffcheck==True and fcheck==1):
                            write_function(x,f)
                            f.write('\n')
                            ffcheck=False                    
                    else:
                        if x.decode()!='<br>':
                            a=write_function(x[:-1],f)
                            f.write('\n')
                    fcheck+=1

if __name__ == "__main__":           
   
    main(station_id,start,end)

