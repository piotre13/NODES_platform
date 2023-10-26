

comp_temp = {
  "basics": {
    "SCEN_CONFIG":{
      "DAYS": 15,
      "RT_FACTOR": None,
      "SCENARIO_NAME": "",
      "START_DATE": ""
    },
    "SIM_CONFIG":{},
    "CONNECTIONS": {},
    "SCEN_OUTPUTS":{}
  },
  "FMU_inst": {
    "fmu_pyfmi_sim": {
      "MODELS": {
        "rc": {
          "ATTRS": [],
          "PARAMS": {
            "fmu_name": "",
            "instance_name": [],
            "num": 0
          },
          "PUBLIC": ""
        }
      },
      "PARAMS": {
        "fmu_log": 0,
        "step_size": 600,
        "stop_time": 31536000,
        "work_dir": "",
      },
      "RUN_PROCESS": {
        "cmd": "python mk_fmu_pyfmi.py %(addr)s"
      }
    }
  },
  "DB_collector": {
  "DB": {
    "attrs": [],
    "step_size": 600
  }
  },
  "timeseries": {
    "timeseries":{
      "RUN_PROCESS": {
        "python": "mk_timeseries:TimeSeriesSim"
      },
      "PARAMS": {
        "start_date": "",
        "stop_date": "",
        "datafile": "",
        "step_size": 3600,
        "conv_dict": {}
      },
      "MODELS": {
        "ts": {
          "PUBLIC": True,
          "PARAMS": [],
          "ATTRS": []
        }
      }
    } },
  "scheduler": {
    "scheduler": {
      "RUN_PROCESS": {
        "python": "mk_scheduler:AgentScheduler",
      },

      "PARAMS": {
        "days": "DAYS"
      },
      "MODELS": {
        "schedule": {
          "PUBLIC": True,
          "PARAMS": {
            "schedule": []
          },
          "ATTRS": []
        }
      }
    }
  },
  "heating_sys": {
    "heating_system": {
      "RUN_PROCESS": {
        "cmd": "python mk_heating_system.py %(addr)s"
      },
      "PARAMS": {
        "step_size": 60
      },
      "MODELS": {
        "hs": {
          "PUBLIC": True,
          "PARAMS": {
            "num": 0,
            "leased_area": 0,
            "EPC_rating": "B",
            "type": "gb",
          },
          "ATTRS": []
        },
        "hp": {
          "PUBLIC": True,
          "PARAMS": {
            "num": 0,
            "leased_area": 0,
            "EPC_rating": "B",
            "type": "hp",
            "COP_nom": 0
          },
          "ATTRS": []
        }
      }
    }
  }

}


