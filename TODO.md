# TODO

- develop a proper logging scheme to collect all simulation information
- resolve the error in co-simulation of Eplus FMUS about the windows calculations
  - identify the buildings
  - understand the problem (probably complex shapes)
- fMU extraction: better management of the script and the folders
  - avoid the main script in each folder if possible
- design and develop a proper way for multi-machine code launching
- automatic scenario creation must be generalized 
  - heat systems attached to the buildings must receive the right net lease area for sizing
- correct path handling everywhere
- update the environment.yml for replicate the environment everywhere
- avoid the printing of eplus in warmup and finalization