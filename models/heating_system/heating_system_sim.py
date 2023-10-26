# -*- coding: utf-8 -*-
"""
Stand-alone black-box Heat Pump model.

@author: Daniele Salvatore Schiera
@maintainer: Daniele Salvaroe Schiera
@status: Development
"""

#TODO aggiungere in futuro, check temperature acqua funzionamento heatpump (e.g caso freezing)

#TODO per heatpump restano due incognite: sizing heating /cooling e mean temperature

# https://www.hosbv.com/data/specifications/14399_Carrier%2030%20AWH%20015%20Specifications.pdf curve di funzionamento heatpump
from __future__ import division

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import interpolate
from scipy.integrate import odeint

PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.append(PROJECT_ROOT)

from coesi.utils import retrive_entity_timeseries_db


class Heating_system():
    def __init__(self, leased_area, EPC_rating, step_size=1, type='hp', storage=False, sizing=True, Text_mean_season=0, V_tank=100,
                 **kwargs):
        # al secondo
        self.leased_area = leased_area
        self.EPC_rating = EPC_rating
        self.type = type
        self.plant = None
        self.storage = storage
        self.storage_bool = storage
        self.sizing_bool = sizing
        self.step_size = step_size
        for key, value in kwargs.items():
            setattr(self, key, value)

        K = [0.5, 1, 1.5, 2, 2.5, 3.2, 3.8, 4.3, 4.7, 5]
        classe = ['A4', 'A3', 'A2', 'A1', 'B', 'C', 'D', 'E', 'F', 'G']
        self.cc = dict(zip(classe, K))

        self.k_factor = self.cc[self.EPC_rating]
        # climatic curve function to obtaint Tw_out
        # self.Tw_cc = lambda Text, k: ((-(Text - 20) * k + 20) < 30) * 30 + (
        #         ((-(Text - 20) * k + 20) >= 30) & ((-(Text - 20) * k + 20) <= 55)) * (-(Text - 20) * k + 20) + (
        #                                      (-(Text - 20) * k + 20) > 55) * 55

        self.Tw_cc = lambda Text, k: ((-(Text - 20) * k + 20) < 18) * 30 + (
                ((-(Text - 20) * k + 20) >= 18) & ((-(Text - 20) * k + 20) <= 55)) * (-(Text - 20) * k + 20) + (
                                        (-(Text - 20) * k + 20) > 55) * 55

        Tw_mean_season = self.Tw_cc(Text_mean_season, self.k_factor)
        self.Tw = Tw_mean_season

        if self.type == 'hp':
            hp_map = pd.read_csv("../models/heating_system/hp_map.CSV", delimiter=';')
            if self.sizing_bool:
                self.Pt_sizing = None
            if hasattr(self, 'COP_nom') == False:
                self.COP_nom = 5
            if hasattr(self, 'EER_nom') == False:
                self.EER_nom = 3
            self.plant = Heat_pump(hp_map, hp_type='aw', COP_nom=self.COP_nom,EER_nom= self.EER_nom, Pt_sizing=self.Pt_sizing, Text_sizing=0,
                                   Text_mean_season=Text_mean_season, EPC_rating=self.EPC_rating,
                                   leased_area=self.leased_area,
                                   Pt_nom=None)
            # init variables
            self.En_el = None # kW
            self.En_auxel = None # kW
            self.COP = None
            self.CR = None
            self.Pel = None


        elif self.type == 'gb':
            if self.sizing_bool:
                self.Pt_sizing = None
            self.plant = Gas_boiler(P_nominal=self.Pt_sizing, leased_area=self.leased_area, k_factor=self.k_factor,step_size=self.step_size)
            # init variables
            self.fuel = None  # kg/s see gas boiler
            self.En_auxel = None  # kW
            self.Pel = None

        if self.storage_bool:
            self.storage = Hot_water_tank(T_start=50, V_tank=V_tank,step_size=self.step_size)
            # init variables
            self.T_tank = None # C




    def step(self, Text, Qt):
        self.Qt = Qt
        if Text > 100:
            Text = Text-273.15
        self.Tw = self.Tw_cc(Text, self.k_factor)
        if self.storage_bool:
            Q_request = (1 * (1 + ((self.Tw - self.storage.T_tank) / (
                        self.storage.T_tank_max - self.storage.T_tank_min)))) * 4185 * (
                                    self.Tw - self.storage.T_tank)  # W
            if Q_request <= 0:
                Q_request = 0
            res_plant = self.plant.step(Text, Q_request)
            res_storage = self.storage.step(Text, Q_request, Qt)
            if self.type == 'hp':
                self.En_el,self.En_auxel, self.COP, self.CR = [x for x in res_plant]
                self.Pel = self.En_el+self.En_auxel
            elif self.type == 'gb':
                self.fuel, self.En_auxel =  [x for x in res_plant]
                self.Pel = self.En_auxel
            self.T_tank = res_storage
            return [res_plant, res_storage, Q_request]
        else:
            res_plant = self.plant.step(Text, Qt)
            if self.type == 'hp':
                self.En_el,self.En_auxel, self.COP, self.CR = [x for x in res_plant]
                self.Pel = self.En_el + self.En_auxel
            elif self.type == 'gb':
                self.fuel, self.En_auxel =  [x for x in res_plant]
                self.Pel = self.En_auxel
            return [res_plant, Qt]


class Heat_pump():
    def __init__(self, hp_map, hp_type='aw', COP_nom=5, EER_nom=3, Pt_sizing=10, Text_sizing=0, Text_mean_season=5, EPC_rating='A',
                 leased_area=None,
                 Pt_nom=None):

        # Parameters
        self.Pt_sizing = Pt_sizing  # at Text_sizing kW
        self.Text_sizing = Text_sizing
        self.Pt_min = 0
        self.COP_nom = COP_nom  # at T7W35
        self.EER_nom = EER_nom # at T18W35
        self.COP_min = 1
        self.hp_type = hp_type
        self.Text_mean_season = Text_mean_season  # Climatic Curve  #
        self.EPC_rating = EPC_rating  # Climatic Curve
        self.leased_area = leased_area

        # Operating temperature limits taken from https://www.hosbv.com/data/specifications/14399_Carrier%2030%20AWH%20015%20Specifications.pdf
        self.Tw_min_heat = 20
        self.Tw_max_heat = 60
        self.Text_min_heat = -20
        self.Text_max_heat = 30
        self.Tw_min_cool = 5
        self.Tw_max_cool = 35
        self.Text_min_cool = 0
        self.Text_max_cool = 50

        # variables
        self.En_auxel = None
        self.COP = None  # plf
        self.COP_fl = None  # full load
        self.CR = None
        self.En_el = None
        self.Pt_hp = None  # # plf
        self.Pt_hp_fl = None  # full load

        hp_map = hp_map.fillna(0)

        hp_map_cool = pd.read_csv('../models/heating_system/hp_map2_cooling.CSV',delimiter=';')
        hp_map_heat = pd.read_csv('../models/heating_system/hp_map2_heating.CSV',delimiter=';')
        # COP e Pt reference to T7W35 and normalization heating
        COP_nom_ref35 = hp_map_heat.loc[hp_map_heat.T_e == 7].loc[hp_map_heat.T_w == 35, 'COP'].values[0]
        hp_map_heat.loc[:, 'COP'] = hp_map_heat.loc[:, 'COP'] / COP_nom_ref35
        Pt_heat_nom_ref35 = hp_map_heat.loc[hp_map_heat.T_e == 7].loc[hp_map_heat.T_w == 35, 'Pt'].values[0]
        hp_map_heat.loc[:, 'Pt'] = hp_map_heat.loc[:, 'Pt'] / Pt_heat_nom_ref35
        # EER e Pt reference to T35W18 and normalization cooling
        EER_nom_ref35 = hp_map_cool.loc[hp_map_cool.T_e == 35].loc[hp_map_cool.T_w == 18, 'EER'].values[0]
        hp_map_cool.loc[:, 'EER'] = hp_map_cool.loc[:, 'EER'] / EER_nom_ref35
        Pt_cool_nom_ref35 = hp_map_cool.loc[hp_map_cool.T_e == 35].loc[hp_map_cool.T_w == 18, 'Pt'].values[0]
        hp_map_cool.loc[:, 'Pt'] = hp_map_cool.loc[:, 'Pt'] / Pt_cool_nom_ref35

        # final maps
        #PTmap = hp_map.pivot_table(values='Pt', index='T_e', columns='T_w')
        #COPmap = hp_map.pivot_table(values='COP', index='T_e', columns='T_w')
        PTmap_heat = hp_map_heat.pivot_table(values='Pt', index='T_e', columns='T_w')
        COPmap_heat = hp_map_heat.pivot_table(values='COP', index='T_e', columns='T_w')
        PTmap_cool = hp_map_cool.pivot_table(values='Pt', index='T_e', columns='T_w')
        EERmap_cool = hp_map_cool.pivot_table(values='EER', index='T_e', columns='T_w')


        # COP correction function for part load operation ASHRAE
        assert self.hp_type in ['ww', 'aw', 'aa']
        if self.hp_type in ['ww']:  # water/water
            C_c = 0.9  # EN14825 default
            self.cop_correction = lambda COP, CR: COP * (CR / (C_c * CR + 1 - C_c))
        elif self.hp_type in ['aw', 'aa']:  # air/water
            C_d = 0.25  # ASHRAE default
            self.cop_correction = lambda COP, CR: COP * (1 - C_d * (1 - CR))

        # Climatic Curve of building based on EPC
        # Caratteristiche curve climatiche e calcolo Twout
        K = [0.5, 1, 1.5, 2, 2.5, 3.2, 3.8, 4.3, 4.7, 5]
        classe = ['A4', 'A3', 'A2', 'A1', 'B', 'C', 'D', 'E', 'F', 'G']
        assert self.EPC_rating in classe
        self.cc = dict(zip(classe, K))

        # climatic curve function to obtain Tw_out
        self.Tw_cc_h = lambda Text, k: ((-(Text - 20) * k + 20) < 30) * 30 + (
                ((-(Text - 20) * k + 20) >= 30) & ((-(Text - 20) * k + 20) <= 55)) * (-(Text - 20) * k + 20) + (
                                             (-(Text - 20) * k + 20) > 55) * 55
        self.Tw_cc_c = lambda Text, k: ((-(Text - 26) * k + 26) < 5) * 5 + (
                ((-(Text - 26) * k + 26) >= 5) & ((-(Text - 26) * k + 26) <= 18)) * (-(Text - 26) * k + 26) + (
                                        (-(Text - 26) * k + 26) > 18) * 18

        #TODO verificare che dimensionamento sia fatto solo per inverno o anche per estate in tal caso una sola tmean o due?
        Tw_mean_season_heat = self.Tw_cc_h(self.Text_mean_season, self.cc[self.EPC_rating])
        Tw_mean_season_cool = self.Tw_cc_c(self.Text_mean_season, self.cc[self.EPC_rating])
        self.Tw_heat = Tw_mean_season_heat
        self.Tw_cool = Tw_mean_season_cool
        # Sizing
        if Pt_nom:
            self.Pt_nom = Pt_nom  # T7W35
            self.Pe_nom = round(self.Pt_nom / self.COP_nom, 2)  # kWt
        else:
            if self.Pt_sizing == None:
                assert self.leased_area != None
                self.Pt_sizing = self.sizing(self.leased_area, self.cc[self.EPC_rating])
            self.Pt_nom_heat = ((0.15 * (7 - (self.Text_sizing)) + self.Pt_sizing + (Tw_mean_season_heat - 35) / 50))  # kWt
            self.Pe_nom_heat = round(self.Pt_nom_heat / self.COP_nom, 2)  # kWt
            self.Pt_nom_cool = ((0.15 * (7 - (self.Text_sizing)) + self.Pt_sizing + (Tw_mean_season_cool - 35) / 50))
            self.Pe_nom_cool = round(self.Pt_nom_cool / self.COP_nom, 2)  # kWt

        self.COP_func_heat = interpolate.interp2d(COPmap_heat.index.values, COPmap_heat.columns.values, COPmap_heat.values.T * self.COP_nom,
                                             kind='linear', bounds_error=False)
        self.Pt_func_heat = interpolate.interp2d(PTmap_heat.index.values, PTmap_heat.columns.values, PTmap_heat.values.T * self.Pt_nom_heat,
                                            kind='linear', bounds_error=False)


        self.COP_func_cool = interpolate.interp2d(EERmap_cool.index.values, EERmap_cool.columns.values, EERmap_cool.values.T * self.EER_nom,
                                             kind='linear', bounds_error=False)
        self.Pt_func_cool = interpolate.interp2d(PTmap_cool.index.values, PTmap_cool.columns.values, PTmap_cool.values.T * self.Pt_nom_heat,
                                            kind='linear', bounds_error=False)


    def sizing(self, leased_area, k_factor):

        self.Pt_sizing = 30 * k_factor / 2.5 / 3412 * leased_area * 10.7639  # kWt
        if leased_area > 500:
            self.Pt_sizing = self.Pt_sizing * 1.1

        return self.Pt_sizing

    def get_cop_pt(self, set_Twout, Text, heating=True):
        if heating:
            if (set_Twout >= self.Tw_min_heat and set_Twout <= self.Tw_max_heat) and (Text >= self.Text_min_heat and Text <= self.Tw_max_heat):
                self.COP_fl = self.COP_func_heat(Text, set_Twout)[0]
                self.Pt_hp_fl = self.Pt_func_heat(Text, set_Twout)[0]
                if self.COP_fl <= self.COP_min:  # OFF COP min
                    self.Pt_hp_fl = 0
                    self.COP_fl = 0
            else:  # OFF out of operating conditions
                self.Pt_hp_fl = 0
                self.COP_fl = 0
        else:
            if (set_Twout >= self.Tw_min_cool and set_Twout <= self.Tw_max_cool) and (Text >= self.Text_min_cool and Text <= self.Tw_max_cool):
                self.COP_fl = self.COP_func_cool(Text, set_Twout)[0]
                self.Pt_hp_fl = self.Pt_func_cool(Text, set_Twout)[0]
                if self.COP_fl <= self.COP_min:  # OFF COP min
                    self.Pt_hp_fl = 0
                    self.COP_fl = 0
            else:  # OFF out of operating conditions
                self.Pt_hp_fl = 0
                self.COP_fl = 0

        return self.COP_fl, self.Pt_hp_fl

    def step(self, Text, Qt):
        if Text > 100:
            Text = Text - 273.15
        Qt = Qt / 1000
        if Qt > 0:
            self.Tw = self.Tw_cc_h(Text, self.cc[self.EPC_rating])
            self.COP_fl, self.Pt_hp_fl = self.get_cop_pt(self.Tw, Text, heating=True)
            if self.Pt_hp_fl != 0:
                self.CR = np.divide(Qt, self.Pt_hp_fl)
                if self.CR < 1:  # parzializzazione
                    self.COP = self.cop_correction(self.COP_fl, self.CR)  # COP correction
                    if self.COP <= self.COP_min:
                        self.COP = self.COP_min
                    self.Pt_hp = Qt
                    self.En_auxel = 0  # (Qt - self.Pt_hp) / 0.98  # =0
                    self.En_el = self.Pt_hp / self.COP
                elif self.CR >= 1:  # hp a pieno carico = pieno potenziale
                    self.Pt_hp = self.Pt_hp_fl
                    self.En_auxel = (Qt - self.Pt_hp) / 0.98  # >0
                    self.COP = self.COP_fl

                    self.En_el = self.Pt_hp / self.COP
            else:  # HP spenta
                self.CR = None
                self.Pt_hp = 0
                self.En_auxel = Qt / 0.98
                self.COP = None
                self.En_el = 0
        elif Qt < 0:  # HP in cooling
            self.Tw = self.Tw_cc_c(Text, self.cc[self.EPC_rating])
            self.COP_fl, self.Pt_hp_fl = self.get_cop_pt(self.Tw, Text, heating=False)
            if self.Pt_hp_fl != 0:
                self.CR = abs(np.divide(Qt, self.Pt_hp_fl))
                if abs(self.CR)< 1:  # parzializzazione
                    self.COP = self.cop_correction(self.COP_fl, self.CR)  # COP correction
                    if self.COP <= self.COP_min:
                        self.COP = self.COP_min
                    self.Pt_hp = abs(Qt)
                    self.En_auxel = 0  # (Qt - self.Pt_hp) / 0.98  # =0
                    self.En_el = self.Pt_hp / self.COP
                elif abs(self.CR) >= 1:  # hp a pieno carico = pieno potenziale
                    self.Pt_hp = self.Pt_hp_fl
                    self.En_auxel = (abs(Qt) - self.Pt_hp)  # la quota di calore che la heatpump non è riuscita a togliere >0
                    self.COP = self.COP_fl
                    self.En_el = self.Pt_hp / self.COP

            else:  # HP spenta
                self.CR = None
                self.Pt_hp = 0
                self.En_auxel = 0
                self.COP = None
                self.En_el = 0
        else:
            self.CR = None
            self.Pt_hp = 0
            self.En_auxel = 0
            self.COP = None
            self.En_el = 0
        return [self.En_el*1000, self.En_auxel*1000, self.COP, self.CR]


class Hot_water_tank():
    def __init__(self, T_start=25, V_tank=100, Q_tank_cap=None, T_tank_max=70, T_tank_min=30,step_size=1):
        self.T_start = T_start
        self.V_tank = V_tank / 1000  # m3
        # vars
        self.T_tank = self.T_start
        self.Q_loss = None
        self.T_tank_max = T_tank_max
        self.T_tank_min = T_tank_min
        self.step_size = step_size
        # init geometry
        if self.V_tank == None:
            assert Q_tank_cap != None
            self.V_tank = self.sizing(Q_tank_cap=Q_tank_cap, T_tank_max=self.T_tank_max, T_tank_min=self.T_tank_min)
        self.aspect_ratio = 3.3
        self.h = (4 * self.V_tank * self.aspect_ratio ** 2 / math.pi) ** (
                1.0 / 3.0)
        if self.h == 0:
            self.r = 0
        else:
            self.r = (self.V_tank / (math.pi * self.h)) ** (
                    1.0 / 2.0)  # tank radius in [m], assuming tank shape is cylinder
        self.surf_area = 2 * math.pi * self.r ** 2 + 2 * math.pi * self.r * self.h  # tank surface area in [m2].
        # assert self.surf_area > 0

        # thermal properties
        self.U_tank = 0.225  # W/m2/K

    def sizing(self, Q_tank_cap, T_tank_max, T_tank_min):
        # calculate tank volume
        Q_tank_capacity_J = Q_tank_cap * 3600  # Wh * s/h = J
        m_tank_kg = Q_tank_capacity_J / (4185 * (T_tank_max - T_tank_min))
        self.V_tank = m_tank_kg / 998.0
        return self.V_tank

    def calc_Q_loss(self, Text):
        self.Q_loss = self.U_tank * self.surf_area * (self.T_tank - Text)
        return self.Q_loss

    def heat_balance(self, y, t, Q_char, Q_loss, Q_disc):
        if self.V_tank == 0:
            dydt = 0
        else:
            mcp_tank = (998.0 * self.V_tank * 4185)  # J/K
            net_energy_flow = (Q_char - Q_loss - Q_disc)  # J/s
            dydt = net_energy_flow / mcp_tank  # K/s
        return dydt

    def step(self, Text, Q_char, Q_disc):
        if Text > 100:
            Text = Text - 273.15
        self.Q_loss = self.calc_Q_loss(Text)
        t = np.linspace(0, self.step_size, self.step_size+1)
        y = odeint(self.heat_balance, self.T_tank, t, args=(
            Q_char, self.Q_loss, Q_disc))
        self.T_tank = y[1][0]
        return self.T_tank


class Gas_boiler():
    def __init__(self, P_nominal=None, leased_area=None, k_factor=None,step_size=1):
        A = 85  # 79.5-85 atm boiler, 89-92 condensing boiler
        B = 2  # 2 "", 1 ""
        C = 81.5  # 76.81.5 "", 95-98
        D = 3  # 3 "", 1 ""
        E = 8.5  # 8-8.5 "", 7-4 ""
        F = -0.4  # -0.27/-0.4 "", -0.37/-0.4
        G = 40  # , 0 ""
        H = 0.148  # , 45 ""
        n = 1  # , 0.48

        if P_nominal == None:
            assert leased_area != None
            self.P_n = self.sizing(leased_area, k_factor)
        else:
            self.P_n = P_nominal  # in kW

        self.step_size = step_size
        self.HHV = 55.5  # MJ/kg
        m_unit = 'kg/s'
        if m_unit == 'kg/s':
            self.HHV_kWh = self.HHV / 3600 * 1000  # kWh/kg
        else: # in Sm3/s
            self.HHV_kWh = self.HHV / 3600 * 1000 / 1.49  # kWh/sM3 KG_to_SM3_metano = 1.49


        self.eff_nominal = (A + B * np.log10(self.P_n)) / 100
        self.eff_partload = (C + D * np.log10(self.P_n)) / 100
        self.q_P0 = (E * self.P_n ** F) / 100
        self.P_auxel_nom = (G + H * self.P_n ** n) / 1000

        self.G_gas = None
        self.P_auxel = None

    def sizing(self, leased_area, k_factor):

        self.P_n = 30 * k_factor / 2.5 / 3412 * leased_area * 10.7639  # kWt
        if leased_area > 500:
            self.P_n = self.P_n * 1.1
        return self.P_n

    def step(self, Text, Qt):
        Qt = Qt / 1000
        beta = Qt / self.P_n
        if beta < 1:  # part load
            Q_gas = Qt / self.eff_partload
            self.G_gas = (Q_gas / self.HHV_kWh) / 3600*self.step_size  # Sm3/s=kW/(kWh/Sm3)*h/s
            self.P_auxel = 0
        elif beta >= 1:  # full
            Q_gas = self.P_n / self.eff_nominal
            self.G_gas = (Q_gas / self.HHV_kWh) / 3600*self.step_size  # Sm3/s=kW/kWh*Sm3*h/s
            Q_aux = Qt - self.P_n
            self.P_auxel = Q_aux
        elif beta == 0:
            Q_gas = self.q_P0
            self.G_gas = (Q_gas / self.HHV_kWh) / 3600*self.step_size  # Sm3/s=kW/kWh*Sm3*h/s
            self.P_auxel = 0
        return [self.G_gas, self.P_auxel*1000]


if __name__ == "__main__":

    import matplotlib.pyplot as plt

    filename = '20220517_RC_modelica_2.hdf5'
    df = retrive_entity_timeseries_db(filename, r'C:\Users\Mocci\PycharmProjects\uesa\Outputs')

    sim = 'fmu_pyfmi_sim-0.rc_mo_0'
    var = 'PHeater'
    Qt = np.array(df[sim][var])  # W
    Text = np.array(df['timeseries-0.ts_0']['DryBulb']) - 273.15
    time = df['time']['t']
    step_size = np.diff(df['time']['t'])[0]

    hs = Heating_system(type='hp', leased_area=150, EPC_rating='D', V_tank=100, storage=True,step_size=300)

    res = []
    for t in range(0, len(time)):
        res.append(hs.step(Text=Text[int(t)], Qt=Qt[int(t)]))

    if hs.type == 'hp':
        En_el = [res[i][0][0] for i in range(0, len(time))]
        En_auxel = [res[i][0][1] for i in range(0, len(time))]
        COP = [res[i][0][2] for i in range(0, len(time))]
        if hs.storage_bool:
            T_tank = [res[i][1] for i in range(0, len(time))]
            Q_req = [res[i][2] for i in range(0, len(time))]
        else:
            Q_req = [res[i][1] for i in range(0, len(time))]

        if hs.storage_bool:
            plt.title('T_tank')
            plt.plot(time, T_tank)
            plt.show()

        print(f'total el: {sum(En_el[300:])}')

        plt.figure()
        plt.plot(time, En_el, label='kWe HP')
        plt.plot(time, En_auxel, label='kWe AUX')
        plt.legend()
        plt.show()

        plt.figure()
        plt.plot(time, COP, label='COP')
        plt.legend()
        plt.show()
    elif hs.type == 'gb':
        G_gas = [res[i][0][0] for i in range(0, len(time))]
        En_auxel = [res[i][0][1] for i in range(0, len(time))]
        if hs.storage_bool:
            T_tank = [res[i][1] for i in range(0, len(time))]
            Q_req = [res[i][2] for i in range(0, len(time))]
        else:
            Q_req = [res[i][1] for i in range(0, len(time))]

        if hs.storage_bool:
            plt.title('T_tank')
            plt.plot(time, T_tank)
            plt.show()

        plt.figure()
        plt.plot(time, En_auxel, label='kWe AUX')
        plt.legend()
        plt.show()

        plt.figure()
        plt.plot(time, G_gas, label='G_has')
        plt.legend()
        plt.show()

    plt.figure()
    plt.plot(time, Qt, label='Qt')
    plt.plot(time, Q_req, label='Qreq')
    plt.legend()
    plt.show()
    #
    #
    # hp_map = pd.read_csv(r"C:\Users\Mocci\PycharmProjects\uesa\coesi\tests\hp_map.CSV", delimiter=';')
    #
    # HP = Heat_pump(hp_map, hp_type='ww', COP_nom=4, Pt_sizing=6, Text_sizing=-5, Text_mean_season=4, EPC_rating='G')
    # tank = Hot_water_tank(T_start=HP.Tw, V_tank=10)
    # gb = Gas_boiler(P_nominal=3.5)
    #
    # res = []
    # rest = []
    # Pt_hp = 0
    # resq_req = []
    # res_gb = []
    # for t in range(0, len(time)):
    #     Q_request = (1 * (1 + ((HP.Tw - tank.T_tank) / (70 - 30)))) * 4185 * (HP.Tw - tank.T_tank)  # W
    #     if Q_request <= 0:
    #         Q_request = 0
    #     res.append(HP.step(Text[int(t)], Q_request / 1000))
    #     tank.step(Text[int(t)], Q_request, Qt[int(t)])
    #     rest.append(tank.T_tank)
    #     resq_req.append(Q_request)
    #     res_gb.append(gb.step(Q_request / 1000))
    #
    # g_gas = [res_gb[i][0] for i in range(0, len(time))]
    # P_auxel_gb = [res_gb[i][1] for i in range(0, len(time))]
    #
    # Pt_hp = [res[i][0] for i in range(0, len(time))]
    # En_auxel = [res[i][1] for i in range(0, len(time))]
    # COP = [res[i][2] for i in range(0, len(time))]
    # En_el = [res[i][3] for i in range(0, len(time))]
    # Tw = [res[i][4] for i in range(0, len(time))]
    # COP_fl = [res[i][5] for i in range(0, len(time))]
    # Pt_hp_fl = [res[i][6] for i in range(0, len(time))]
    # CR = [res[i][7] for i in range(0, len(time))]
    #
    # plt.title('T_tank')
    # plt.plot(time, rest)
    # plt.show()
    # plt.title('Qrequest')
    # plt.plot(time, resq_req)
    # plt.show()
    #
    # plt.figure()
    # plt.plot(time, En_el, label='kWe HP')
    # plt.plot(time, En_auxel, label='kWe AUX')
    # plt.legend()
    # plt.show()
    #
    # plt.figure()
    # plt.plot(time, Qt, label='Qt')
    # plt.plot(time, np.array(Pt_hp) * 1000, label='Pt_hp')
    # plt.legend()
    # plt.show()
    #
    # plt.figure()
    # plt.plot(time, COP_fl, label='COP_fl')
    # plt.plot(time, COP, label='COP')
    # plt.legend()
    # plt.show()
    #
    # plt.figure()
    # plt.plot(time, Tw, label='Twout')
    # plt.legend()
    # plt.show()
    #
    # # plt.figure()
    # # plt.plot(time, Text, label='Text')
    # # plt.legend()
    # # plt.show()
    #
    # plt.figure('Pt')
    # plt.plot(time, Pt_hp_fl, label='Pt_hp_fl')
    # plt.legend()
    # plt.show()

    ## PLOT HP COP AND PT MAPS
    # w = hp_map.T_w.unique()
    #
    # tt = np.linspace(-15,12)
    # ww = np.linspace(w.min(),w.max())
    #
    # x, y = np.meshgrid(tt,ww)
    #
    # H = HP.COP_func(tt, ww)
    # fig = plt.figure()
    # plt.title('COP map')
    # plt.contourf(x,y,H)
    # #plt.axis('scaled')
    # plt.colorbar()
    # plt.xlabel('Text')
    # plt.ylabel('Twat')
    # plt.show()
    #
    # H = HP.Pt_func(tt, ww)
    # fig = plt.figure()
    # plt.title('Pt map')
    # plt.contourf(x, y, H)
    # #plt.axis('scaled')
    # plt.colorbar()
    # plt.xlabel('Text')
    # plt.ylabel('Twat')
    # plt.show()
    #
    # PTmap = hp_map.pivot_table(values='Pt', index='T_e', columns='T_w')
    # H = PTmap / hp_map.loc[hp_map.T_e == 7].loc[hp_map.T_w == 35, 'Pt'].values[0] * HP.Pt_nom
    # plt.contourf(H.index.values, H.columns.values, H.values.T)
    # plt.show()
    #
    # COPmap = hp_map.pivot_table(values='COP', index='T_e', columns='T_w')
    # H = COPmap / hp_map.loc[hp_map.T_e == 7].loc[hp_map.T_w == 35, 'COP'].values[0] * HP.COP_nom
    # plt.contourf(H.index.values, H.columns.values, H.values.T)
    # plt.show()
