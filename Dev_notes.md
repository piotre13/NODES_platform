# Note

# for REAL TIME IN ARGO
PER FUNZIONARE MATLAB è NECESSARIO ENTRARE CON SSH -y ALTRIMENTI SI BLOCCA. NON è DATO SAPERSI IL MOTIVO MA FUNZIONA.


Useful linux bash command

ps aux | grep [nomeprocesso]

sudo kill -9 [nome processo o cod]



## RC Modelica extraction

per usare Aixlib e 1.0.0 e Buildings 8.0.0 dava errore per compilare l'efmu da un building fatto con queste libreri. 
Dal log emerge che manca ModelicaUtilities.h. ho aggiunto tale file nella folder C-Sources delle relative libreria (ModelicaUtilities.h prese da Modelica 2.3.2)

Le FMU estratte da Modelica vengono risolte con metodo EULERO!! non usano il solver avanziati tipo Dassl!! questo è importante perche significa che è importante settare il timestep per il metodo euler
in dassl si ha il controllo dello step size!! quindi molto piu flessibile

euler - Euler - explicit, fixed step size, order 1

assl - default solver - BDF method - implicit, step size control, order 1-5 non è supportata in FMU

è possibile provare CVODE ma è una funzionalità nuova e potrebbe non funzionare

There are multiple ways of exporting Modelica models as FMU from OMEdit. I will restrict myself to the C FMUs here, but you can do most of this (but not all) for C++ FMUs as well.
(con Dymola esporta FMU con CVode e funziona!!!)

If you just go File->Export->FMU you will get a 2.0 FMU with ModelExchange (ME) and Co-Simulation(CS) an an explicit Euler as integrator.
If you want to change some FMU export settings you can use the Options from Tools->Options->FMI to export e.g. only a CS FMU and for a specific platform.

When you use the scripting commands `buildModelFMU` or`translateModelFMU`, seeOpenModelica Scripting API, with the OpenModelica Compiler CLI from OMEdit you have more options.

But if you want to change the internal integrator for a CS FMU you have to use the Compiler Flag `--fmiFlags=s:cvode`. Please note that this feature is very new and currently the only setting you can change is the internal integrator used for `fmi2DoStep`.
You can pass it with the CLI

Code:

>setCommandLineOptions("-d=newInst --fmiFlags=s:cvode")
true
>buildModelFMU(Modelica.Electrical.Analog.Examples.CauerLowPassSC,"2.0","cs")


## Log level of FMU in PYFMI

NOTHING = 0
FATAL = 1
ERROR = 2
WARNING = 3
INFO = 4
VERBOSE = 5
DEBUG = 6
ALL = 7


##
You can also  in the command line to generate a requirements.txt
run pip freeze > requirements.txt

assert <variable> condizione
se avviene si blocca l'esecuzione (usato epr debug)

in mosaik il simualtore lo ritrovo sotto:
NOMEInstanzaModelle._inst.simulator.


## energyplus to FMU: EP2FMU

seguire le istruzione. é necessario installare il compiler VS con il build tools per operare da linea di comando. serve 
pUNTARE ANCHE VISUAL STUDIO ANDANDO A MODIFICARE LA PATH NELLA CARTELLA SCRIPTS in tutti i .bat
per far funzionare E+ con FMU aggiungere in path anche la dir di energy plus
E+ e file posso governarli da eppy.py
nel file idf bisogna aggiungere l'absolute path per gli oggetti che vengono prese dal dataset di E+
nel file idf, in simulation control bisogna aggiungere il Run Period al weather
Leggere attentamente i punti a pagina 21 per la compatibilita dell'FMU da E+ nella userGuide della libreria energyplustoFMU.


**ATT**: una volta che si attivano le interfacce esterne su eplsu (tipo meteo) devono essere usate! altrimenti si terranno il valore iniziale di input!

## PyFMI:
**IMP!!!**
forse non si deve usare il get() nella fase iniziale. se chiedo all'fmu i valori iniziali delle varaibili di input non me li da (mi riporta zero, ma so che 
non è vero se li ho impostati nel simulatore di origine diversi da zero es in energy plus)
forse dipende da get_variable_fixed()¶ e posso vederlo da get_variable_start() che mi da il valore di partenza impostato in e+.
Dunque prende come valore questo di partenza. 
PER E+ in FMU (CS1.0): In sostanza il get() mi da sempre zero per le variabili di input. E viceversa set() non va se lo faccio per le variabili di output.
Sapendo la condizione iniziale, ed impostando poi la stessa condizione in input, non ottengo lo stesso risultato all'inizio (ho un balzo)
Per non avere problemi in E+ impostare tutte le interfacce con valori iniziali nulli o comunque che siano non influenti.
FMU CS2.0: se faccio get() ottengo il valore indipendentemente se è input o output; se faccio set() setta il valore per gli input (OK) ma sembra farlo anche per i parametri o altri variabili (??)
ma non quelli definiti come Output (OK)
# pyfmi oppure usare fmpy (più supportato e facile da leggere)

FMI
--> Between fmi2DoStep you can only set Real variables that have causality="input" or causality="parameter" and variability="tunable" - and an input with an equation doesn't qualify.
SEE FMI DOCUMENTATION
VARIABLES:
Causality:
- Parameter;
- Calculated_Parameter;
- Input;
- Output;
- Local;
- Independent;
- Unknown.
Variability:
- Constant;
- Fixed;
- Tunable (value of variable is constant between external events (ME) and between Communication Points (CS);
- Discrete;
- Continuous;
- Unknown.
Initial:
- exact;
- approx;
- calculated.

LE chiamate set() e get() devono essere fatte senza riperete get() prima di un'altro step! sequanza corretta in DOC

ALTRA COSA IMPORTANTE. LE variabili che sono considerate PARAMETRI FIXED possono essere settate ma PRIMA dell'inizializzazione!!! e non durante la simulazione!!
da MODELICA un parametro puo diventare "tunable" se si aggiunge annotation(Evaluate=False)


## Energy plus in fmu
Da simulazione diretta con simulate() posso dare input anche con diversi timestep. è necessario però andare a definire i 
number of communication point, cioè se io do un input che è con timestep 5 secondi, ma il modello interno lavora a timestep 
di 100, allora se voglio simulare da 0 a 200 gli ncp sono 2 a prescindere dall'input.
Inoltre la simulazione in energy plus non da output allo step zero. Con pyfmi potrei ottenerlo

## MOSAIK

Start simulators: use the init() parameters

instantiating models: use the create() parameters

connect entities

running simulation

SIMULATOR

package of models of a certain type / use / definition /system

**init** defines the simulator general parameters

MODELS: are the different type of models provided by the simulator with their model parameters and attributes

**create** a certain number of instances of a single *model* using the provided model parameters

**step** performs a simulation step (using the time of mosaik as input)

E+
idf_steps_per_hour = 6 # DEFAULT SET in E+ from fmu and minimum simulation time for E+ is a DAY

Mosaik 

How to Active Circular data flow

connect(A,B) and connect(B,A) like the case of control strategies:

    connect(A, B, 'state')
    connect(B, A, 'schedule')

For passive control strategies

connect(A, B, 'state')
connect(B, A, 'schedule', delay=True)

The data-flows in the example above are passive, meaning that A and B compute data hoping that someone will use them. This abstraction works reasonably well for normal simulation models, but control mechanism usually have an active roll. They actively decide whether or not to send commands to the entities they control.

Active control strategies:
a solution is the use of async_request

connect(A, B, 'state', async_request=True)

This prevents A from stepping too far into the future so that B can get additional data from or set new data to A in B.step()
we have to add in B.step() the method set_data()
WE can use the second possibility OR
better the following way (without to specify data exchange within the simulator B via set_data):

Example

As an example, take three simulators A, B and C that are to be connected in the way A → B, B → C, C → A. After establishing the first two connections, mosaik will prohibit the third one since it might lead to deadlocks. It is allowed, however, when established via
world.connect(src, dest, (‘c_out’, ‘a_in’), time_shifted=True, initial_data={‘c_out’: 0})
This connection will always be handled after all other connections and provide data to A only for its next time step. This way, deadlocks are avoided. However, input data for the initial step of A has to be provided. This is done via the initial_data argument. In this case, the initial data for ‘a_in’ is 0.

# **How to do real-time simulations**

It is very easy to do real-time (or “wall-clock time”) simulations in mosaik. You just pass an *rt_factor* to **`[World.run()](https://mosaik.readthedocs.io/en/latest/api_reference/mosaik.scenario.html#mosaik.scenario.World.run)`** to enable it:
world.run(until=10, rt_factor=1)


# Installare matlab engine in python MATLAB
bisogna avviare una sessione per ofni FMU di MATLAB? non funziona.
Funziona se avvio 2 sessione per una FMU importata in mosaik (con altre due FMU)
! pyfmi potrebbe creare due instanze di un modollo qunado faccio instanziate e initialize
SI conferma che pyfmi crea due INSTANZE ecco perchè servivano due seissione di MATLAB 
con fmpy risolto il problema 


# MOSAIK 
QUANDO INIZIA la simulazione a t=0 mosaik esegue subito lo steo da t=0 a t=step. Solo successivamente salva i dati, quindi salva i dati già allo step 1 però nello step temporale 0. nelle fmu questo è risolto salvando i dati allo start e poi facendo lo step come se fosse t- step precendente cosi da allinearsi. questo non viene però fatto con gli altri simulatori VERIFICARE se CAUSA DIFFERENZE

## Avvio Solver MAtlab
matlab viene avviato attraverso un'estra function che chiama un subprocess per avviare uno script di matlab che serve per lanciare delle sessioni di matlab ad hoc per FMI Co-sim

## Modelica IMPORTANTE
Se da modelica extraggo una FMU contenente solo ad esempio un blocco sorgente segnale sinusoidale, questo non funziona.. in python con FMPY non viene elaborato.. come se mancasse il tempo

CON pyFMI invece funziona!!! come mai?? da approfondire (test_fmpy3 e pyfmi_test1 adibiti a questi test)


## CONNESSIONE IN CMD 
problema con socket non bloccanti e bloccanti
 'DB': {
        'cmd': r'C:\Users\DANIEL~1\pycharm_project\envs\Scripts\mosaik-hdf5 %(addr)s', FUNZIONA
        
    se faccio 'cmd' : mosaik-hdf5 %(addr)s non si riesce a connettere
    
    
    se faccio cmd simulator %(addr)s senza mettere l'estenzione (tipo .py) significa che è un .exe quindi avviato con qindow. i simulatori installati cosi si usano in questo modo ma vorrei poterlo usare direttamente
    
    
    in base.py sotto calsse BaseTCPSocket c'è il setblocking(0). anche mettendo uno il simulatore partema non riceve nulla..
    
    
    RISOLTO!!! MANCAVA if __name__ == '__main__': ALLA FINE! POICHè ERA STRUTTURATO COME MODULO INSTALLATO AVAVE ALLA FINE IL main() E NON if __name__ == '__main__':!!
    
## NOTA IMP SUI SIMULATORI MK_SIMS
poichè i simualtori possono essere anche runnati anche come subprocess, è necessario che importino delle direcotry o metodi ecc in maniera indipendente. considerando che l'esecuzione del simulatore, se fatto tramite cmd avra come directoru principale proprio dove si trova il simulatore!!

## SE da errore could not connect to moisak. meglio riavviare e dovrebbe funzionare

# COSTRUIRE un DEFAULT YAML PER OGNI MOSAIK API!!!! IMPORTANTE PER DEFINIRE TUTTE LE VARIABILI CHE SI POSSONO USARE E COME USARLI
# IN QUESTO MOMENTO I TEST_<modello>.yaml danno una idea di template
