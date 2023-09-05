============================================================
Co-simulation for Energy Systems Integration (COESI)
============================================================

Platform Overview
=================
COESI will consist of a tool-chain to perform simulation of dynamic systems of different urban energy scenarios and use cases.
The simulation framework uses Mosaik as the co-simulation engine, which exposes API to integrates different simulators of models.
A simulator consist in the application of the Mosaik API to the model itself in order to use it in the scenario developed into Mosaik.
The simulators can be diverse, e.g. data visualization, physical models, Multi-Agent System models, control models etc. Two simulators were developed to use FMU through the python libraries pyFMI and FMPy. Some of the already developed simulators were used adn adapted for our platform.

Documentations
=================

How to install
--------------
Install python 3.8+ (64 bit)

visualstudio install builtools


Install miniconda

conda env create --file environment.yml


install IDE (PyCharm or spyder)

clone the repository uesa .command.


activate administrator access

How to use it
--------------
From command line, activate the environment:

::

 activate uesa

Go to uesa directory of the project. To run a simulation run the following command:

::

 python main.py

to run the simulation of demo scenario.
if you want to choose the scenario and/or activate the web dashboard, run the following command:

::

 python main.py -s <scenario_name.yaml> -w <bool>

where <scenario_name.yaml> is the namefile of the scenario located in the scenarios directory. For <bool>, set 1/0 if you want to activate/deactivate the web dashboard


to run a fmu with fmpy gui
python -m  fmpy.gui

to check fmu
python fmuchecker.py

Authorship Information
===========================
Research group of Politecnico di Torino Energy Center Lab.

- author: Daniele Salvatore Schiera, Pietro Rando Mazzarino
- credits: Energy Center Lab research group
- maintainer: Daniele Salvatore Schiera, Pietro Rando Mazzarino
- email: daniele.schiera@polito.it, pietro.randomazzarino@polito.it
- status: Development
