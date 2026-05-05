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


def collect_results_stats(Result_File_path,Fault_buses,Fault_types,Fault_Res,nIBR,ACC=1.0,IBR_LOC=None,details=False):
    Sim_Data = pd.read_csv(Result_File_path,header=None)
    Results = []
    for row in Sim_Data.iterrows():
        Bus = row[1][0]
        Fres = row[1][2]
        Ftype = row[1][3]
        Con_str = row[1][16]
        
        if(Con_str>0 and Con_str<999):
            Results.append([Bus,Ftype,Fres,Con_str])
        elif(Con_str>=999 and Con_str<=1998):
            Results.append([Bus,Ftype,Fres,Con_str])
        else:
            Results.append([Bus,Ftype,Fres,None])

    if(IBR_LOC):
        nIBRs = len(IBR_LOC)
    else:
        nIBRs = nIBR
    
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
capedbloc = r"C:\Users\tpatel\Documents\APA_Python\IEEE14_MLData.gdb" 
con = APApy.connect_to_DB(capedbloc)

# %% 
TableNames = APApy.get_TableNames(con)# GET Database Table Names 
Tables = APApy.get_Tables(con,TableNames) # Get all tables
# %% Get IBR Buses
Buses = APApy.get_Buses_info(con)
Lines = APApy.get_lines_info(con)
Switches = APApy.get_switches_info(con)

IBR_Tags = [x['GENERATOR_TAG'] for x in Tables['EPRI_WTG_DATA']]
CAPE_Machines_Bus_Tag = [(x['BUS_NUMBER'],x['TAG'],x['USE_CURRENT_LIMIT']) for x in Tables['MACHINE_DATA'] ]
IBR_Buses = []  
for IBR_Tag in IBR_Tags:
    Ibr_bus = [x[0] for x in CAPE_Machines_Bus_Tag if x[1] == IBR_Tag and x[2] == 4]
    if(Ibr_bus):
        for bus in Ibr_bus:
            IBR_Buses.append(bus)


recordTags = [28]
recorderLoc = [{'Name':x['Name'],'Bus1':x['Bus1'],'Bus2':x['Bus2'],'Circuit':x['Circuit'],'Tag':x['Tag']} for x  in Lines if x['Tag'] in recordTags] 
recorderLoc += [{'Name':x['Name'],'Bus1':x['Bus1'],'Bus2':x['Bus2'],'Circuit':0,'Tag':x['Tag']} for x  in Switches if x['Tag'] in recordTags] 

# Close DB connection before sunning Cape
con.close()
# %%Select Fault buses 

# Selest all load buses ignoring IBR buses and slack bus
Fault_buses = [x['Number'] for x in Buses if (x['Number'] not in IBR_Buses) and x['Number'] != 1]

# define Faults types and resistacne 
Fault_types = ['ABC','BC','AG']
Fault_Res_mag = [100,95,90,85,80,75,70,65,60,55,50,45,40,35,30,25,20,15,12.5,10,9,8,7,6,5,4,3,2,1,0.75,0.5,0.25,0.1,0]

Fault_Res = []
[Fault_Res.append(x) for x in Fault_Res_mag]
Fault_Res_con = [complex(round(x.real,3),round(x.imag,3)) for x in Fault_Res]

Fault_buses = [21] # list of fault bus locations
nIBR=1
# %% Run Simulation 
# wcape.exe file pat
cape_path = r"C:\Program Files\Siemens\APA16\progs\apa.exe"
# dir contaning script
script_files = os.getcwd()+'\\'
# CUPL script name
script_file_name = "Test_Fault_sim"
# Simulation Result Report 
Result_File1 = os.getcwd()+'\\'+'APA_fault_report_MLDataUN1.csv'
ACC_Factor1 = 1.0
# simulate Faults and collect Data
start_Time = time.time()
script_abs_path = APApy.write_short_circuit_script(cape_path,
                                                    script_files,script_file_name,
                                                    capedbloc,
                                                    Fault_buses,Fault_Res_con,Fault_types,
                                                    Result_File1,
                                                    ACC_Factor=ACC_Factor1,
                                                    record_FaultBus=False,
                                                    record_IBRstatus=[],
                                                    recorder_LOCarray=recorderLoc,
                                                    closeAPA=True)

APApy.run_CUPL_script(cape_path,script_abs_path,nogui=True)

# %% Read Results
Result_stats1 = collect_results_stats(Result_File1,Fault_buses,Fault_types,Fault_Res_con,nIBR,ACC=ACC_Factor1,IBR_LOC=[20],details=True)
stop_time = time.time()
ex_time = stop_time-start_Time
print(ex_time)

# %% misc 

# Set acc factors 

#  MXI_VCCS_ACCEL_CONSTANT On 
#  MXI_ACCELERATOR_FACTOR_VCCS 1.00 
#  MXI_BESS_ACCEL_CONSTANT On 
#  MXI_ACCELERATOR_FACTOR_BESS 1.00 
#  MXI_EPRI_IV_ACCEL_CONSTANT On 
#  MXI_ACCELERATOR_FACTOR 0.3 
#  MXI_EPRI_III_ACCEL_CONSTANT On 
#  MXI_ACCELERATOR_FACTOR_EPRI_III 1.00


# For adaptive acceleration factor: 

# MXI_VCCS_ACCEL_CONSTANT On 
#  MXI_ACCELERATOR_FACTOR_VCCS 1.00 
#  MXI_BESS_ACCEL_CONSTANT On 
#  MXI_ACCELERATOR_FACTOR_BESS 1.00 
#  MXI_EPRI_IV_ACCEL_CONSTANT Off 

# MXI_ACCELERATOR_FACTOR_ADAP_MIN 0.2 
#  MXI_ACCELERATOR_FACTOR_ADAP_MAX 0.8 

# MXI_EPRI_III_ACCEL_CONSTANT On 
#  MXI_ACCELERATOR_FACTOR_EPRI_III 1.00
