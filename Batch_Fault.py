# -*- coding: utf-8 -*-
"""
Created on Wed Feb  4 12:06:20 2026

@author: tpatel
"""

# %%
import os
import time
import APApy
import pandas as pd


# %% Functions 
def collect_results_stats(Result_File_path,Fault_buses,Fault_types,Fault_Res,ACC=1.0,IBR_LOC=[],details=False,header_row=0):
    Sim_Data = pd.read_csv(Result_File_path,header=header_row)
    Results = []
    for row in Sim_Data.iterrows():
        Bus = row[1][0]
        Fres = row[1][2]
        Ftype = row[1][3]
        Con_str = row[1][28]
        
        if(Con_str>0 and Con_str<999):
            Results.append([Bus,Ftype,Fres,Con_str])
        elif(Con_str>=999 and Con_str<=1998):
            Results.append([Bus,Ftype,Fres,Con_str])
        else:
            Results.append([Bus,Ftype,Fres,None])

    if(IBR_LOC):
        nIBRs = len(IBR_LOC)
    else:
        nIBRs = 0
    
    converged_fault_iters = [x[3] for x in Results if x[3]]
    nFaults = len(Fault_buses)*len(Fault_types)*len(Fault_Res)
    fault_converged = len(converged_fault_iters)
    fault_failed = len([1 for x in Results if x[3] is None])
    
    max_number_of_iters = max(converged_fault_iters)
    min_number_of_iters = min(converged_fault_iters)
    avg_number_of_iters = sum(converged_fault_iters) / fault_converged

    Result_stats = {'nFaults':nFaults,
                    'nIBRs':nIBRs,
                    'nConverged':fault_converged,
                    'nFailed':fault_failed,
                    'maxIter':max_number_of_iters,
                    'minIter':min_number_of_iters,
                    'avgIter':avg_number_of_iters,
                    'IBR_LOCS':IBR_LOC,
                    'ACC_IV': ACC}
    if(details):
        Result_stats['Results'] = Results
    return Result_stats

# %% Connect CAPE Database 
# APA database path
capedbloc = os.getcwd() + r"\APA_converge\IEEE14_ConCh.gdb"     
con = APApy.connect_to_DB(capedbloc)

# %% get Database Tables
TableNames = APApy.get_TableNames(con)# GET Database Table Names 
Tables = APApy.get_Tables(con,TableNames) # Get all tables

# %% Get IBR Buses
Buses = APApy.get_Buses_info(con)
Lines = APApy.get_lines_info(con)
Switches = APApy.get_switches_info(con)

IBR_Tags = [x['GENERATOR_TAG'] for x in Tables['EPRI_WTG_DATA']]
Machines_Bus_Tag = [(x['BUS_NUMBER'],x['TAG'],x['USE_CURRENT_LIMIT']) for x in Tables['MACHINE_DATA'] ]
IBR_Buses = []  
for IBR_Tag in IBR_Tags:
    Ibr_bus = [x[0] for x in Machines_Bus_Tag if x[1] == IBR_Tag and x[2] != 0]
    if(Ibr_bus):
        for bus in Ibr_bus:
            IBR_Buses.append(bus)

# define Relay locations to record 
recordTags = []
recorderLoc = [{'Name':x['Name'],'Bus1':x['Bus1'],'Bus2':x['Bus2'],'Circuit':x['Circuit'],'Tag':x['Tag']} for x  in Lines if x['Tag'] in recordTags] 
recorderLoc += [{'Name':x['Name'],'Bus1':x['Bus1'],'Bus2':x['Bus2'],'Circuit':0,'Tag':x['Tag']} for x  in Switches if x['Tag'] in recordTags] 

# Close DB connection before sunning Cape
con.close()
# %%Select Fault buses 

# Selest all load buses ignoring IBR buses and slack bus
Fault_buses = [x['Number'] for x in Buses if (x['Number'] not in [x[0] for x in Machines_Bus_Tag]) and x['Number'] != 1]

# define Faults types 
Fault_types = ['ABC','BC','AG']

# define fault Z
Fault_Res_mag = [0.1]
Fault_Res = []
[Fault_Res.append(x) for x in Fault_Res_mag]
Fault_Res_con = [complex(round(x.real,3),round(x.imag,3)) for x in Fault_Res]

# %% Run Simulation 
# wcape.exe file pat
cape_path = r"C:\Program Files\Siemens\APA16\progs\apa.exe"
# dir contaning script
script_files = os.getcwd()+'\\'
# CUPL script name
script_file_name = "Test_ACC_Fault_sim"
# Simulation Result Report 
Result_File1 = os.getcwd()+'\\'+'APA_ACC_fault_report.csv'

# specify accleartion factors 

# ACC_Factor1 = {'VCCS': 0.1,
#                'EPRI_Type_IV':[0.29,0.71],
#                'EPRI_Type_III':0.4,
#                'BESS':0.6
#                }

ACC_Factor1 = 0.5

# simulate Faults and collect Data
start_Time = time.time()
# write CUPL script
script_abs_path = APApy.write_short_circuit_script(script_files,
                                                   script_file_name,
                                                    capedbloc,
                                                    Fault_buses,Fault_Res_con,Fault_types,
                                                    Result_File1,
                                                    ACC_Factor=ACC_Factor1,
                                                    record_FaultBus=True,
                                                    recorder_LOCarray=recorderLoc,
                                                    closeAPA=False,
                                                    header=None)    # Must be None , need find fix

# run Script
APApy.run_CUPL_script(cape_path,script_abs_path,nogui=False)

# %% Read Results from csv file
Result_stats1 = collect_results_stats(Result_File1,Fault_buses,Fault_types,Fault_Res_con,ACC=ACC_Factor1,IBR_LOC=IBR_Buses,details=True,header_row=None)

stop_time = time.time()
ex_time = stop_time-start_Time
print(ex_time)
