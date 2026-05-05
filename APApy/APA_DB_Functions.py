# -*- coding: utf-8 -*-
"""
Created on Thu Jan 22 15:18:05 2026

@author: tpatel
"""

# %% imports 
import fdb
import subprocess
import signal
import psutil
from enum import Enum

# %% Access Database info
def connect_to_DB(DB_path,user='sysdba', password='masterkey'):
    try:
        con = fdb.connect(dsn=DB_path, user=user, password=password)
    except fdb.Error as e:
        return f"Error connecting to FDB database: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    return con

def get_fdb_cursor(con):
    try:
        cur = con.cursor()
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    return cur
        
def get_Table_Data(con,Table_Name):
    
    cursor = get_fdb_cursor(con)
    cursor.execute("SELECT * From "+Table_Name)
    Tab_Fields = [desc[0] for desc in cursor.description]
    Tab_Data = cursor.fetchall()
    CAPE_Tab = [dict.fromkeys(Tab_Fields) for ii in range(len(Tab_Data))];
    for ii in range(len(CAPE_Tab)):
        for jj in range(len(CAPE_Tab[ii].keys())):
            key = Tab_Fields[jj]
            CAPE_Tab[ii][key] = Tab_Data[ii][jj]
    
    cursor.close()
    return CAPE_Tab

def get_Tables(con,Table_Names):
    Tabs = {}
    for Tab_Name in Table_Names:
        Tab = get_Table_Data(con,Tab_Name)
        Tabs[Tab_Name] = Tab
    return Tabs

def get_TableNames(con):
    schema1=fdb.schema.Schema()
    schema1.bind(con)
    
    nTables = len(schema1.tables)
    TableNames = [None]*nTables
    for ii in range(nTables):
        TableNames[ii] = schema1.tables[ii].name        
    return TableNames 

def check_sql_str(con,check_str):
    cursor = get_fdb_cursor(con)
    try:
        cursor.execute(check_str)
    except fdb.Error as e:
        print(f"Error: {e}")
        return -1
    result = cursor.fetchone()
    return result

# %% Get Network Info
def get_lines_info(con):
    CAPE_Buses = get_Table_Data(con,'BUS_DATA')
    CAPE_Lines = get_Table_Data(con,'LINE_COMMON_DATA')
    CAPE_Lines2 = get_Table_Data(con,'BRANCH_TWO_PORT_MODEL_DATA')
    Lines = []
    for CLine in CAPE_Lines:
        Line = {}    
        Line['Name'] = CLine['LINE_NAME'].strip()
        Line['Tag'] = CLine['BRANCH_TAG']
        Line['Circuit'] = CLine['CIRCUIT_NUMBER']
        Line['Bus1'] = CLine['FROM_BUS_NUMBER']
        Line['Bus2'] = CLine['TO_BUS_NUMBER']
        Line['phases'] = CLine['PHASES']
        Line['numPhases'] = len(CLine['PHASES'])
        Line['Length'] = CLine['LINE_LENGTH']
        Line['Enabled'] = CLine['TO_BUS_BKR_STATUS'] == 'C' and CLine['FROM_BUS_BKR_STATUS'] == 'C'
        Line["isSwitch"] = False   
        #Line["kV"] = 
        
        CAPE_Lines2_id = [x['BRANCH_TAG'] for x in CAPE_Lines2].index(CLine['BRANCH_TAG'])
       
        Line['R1pu'] = CAPE_Lines2[CAPE_Lines2_id]['POSITIVE_SEQ_ZKM_REAL']
        Line['X1pu'] = CAPE_Lines2[CAPE_Lines2_id]['POSITIVE_SEQ_ZKM_IMAG']
        Line['B1pu'] = CAPE_Lines2[CAPE_Lines2_id]['POSITIVE_SEQ_YK_IMAG'] * 2
        
        Line['R1pu'] = CAPE_Lines2[CAPE_Lines2_id]['NEGATIVE_SEQ_ZKM_REAL']
        Line['X1pu'] = CAPE_Lines2[CAPE_Lines2_id]['NEGATIVE_SEQ_ZKM_IMAG']
        Line['B1pu'] = CAPE_Lines2[CAPE_Lines2_id]['NEGATIVE_SEQ_YK_IMAG'] * 2
        
        Line['R0pu'] = CAPE_Lines2[CAPE_Lines2_id]['ZERO_SEQ_ZKM_REAL']
        Line['X0pu'] = CAPE_Lines2[CAPE_Lines2_id]['ZERO_SEQ_ZKM_IMAG']
        Line['B0pu'] = CAPE_Lines2[CAPE_Lines2_id]['ZERO_SEQ_YK_IMAG'] * 2

        CAPE_BUS_id = [x['BUS_NUMBER'] for x in CAPE_Buses].index(CLine['FROM_BUS_NUMBER'])
        if(Line['numPhases'] > 1):
            LL_factor = 3**0.5
        else:
            LL_factor = 1
        
        Line['kV'] = CAPE_Buses[CAPE_BUS_id]['BASE_KV']/LL_factor
        #Line['Rpu']: CAPE_Lines2[CAPE_Lines2_id][]
        #Line['Xpu']: 0.044661458274999996
        
        Zb = ((CAPE_Buses[CAPE_BUS_id]['BASE_KV'])**2)/100 # 100 MVA assumed 
        Line['R1_ohm_km'] = Line['R1pu'] * Zb   # pu/km>ohm/km  
        Line['R0_ohm_km'] = Line['R0pu'] * Zb   
        Line['X1_ohm_km'] = Line['X1pu'] * Zb   # pu/km>ohm/km  
        Line['X0_ohm_km'] = Line['X0pu'] * Zb       
        
        Yb = 1/Zb
        
        Line['B1_uS_km'] = Line['B1pu'] * Yb * (1e6) # pu/km>s/km  S/km>uS/km
        Line['B0_uS_km'] = Line['B0pu'] * Yb * (1e6)  
        
        Lines.append(Line)
    return Lines

def get_Buses_info(con):
    CAPE_Buses = get_Table_Data(con,'BUS_DATA')
    Buses = [] #[dict.fromkeys(['Name', 'nodes', 'numPhases', 'X', 'Y', 'kV']) for x in CAPE_Buses]
    for CBus in CAPE_Buses:
        Bus ={}
        Bus['Name'] = CBus['BUS_NAME'].strip()
        Bus['Number'] = CBus['BUS_NUMBER']
        Bus['nodes'] = [1,2,3] 
        Bus['numPhases'] = 3
        Bus['X'] = 0
        Bus['Y'] = 0
        if(Bus['numPhases'] > 1):
            LL_factor = 3**0.5
        else:
            LL_factor = 1
        Bus['kV'] = CBus['BASE_KV']/LL_factor
        Bus['Vpre_mag'] = CBus['PREFAULT_VOLTAGE_MAGNITUDE']
        Bus['Vpre_ang'] = CBus['PREFAULT_VOLTAGE_ANGLE']
        Bus['Type'] = CBus['BUS_TYPE']
        Buses.append(Bus)
    return Buses

def get_Loads_info(con):
    CAPE_Loads = get_Table_Data(con,'LOAD_DATA')
    Loads = []
    for CLoad in CAPE_Loads:
        Load = {}
        Load['Name'] = CLoad['BRANCH_NAME'].strip()
        Load['Bus'] =  CLoad['BUS_NUMBER']
        Load['P_MW'] = CLoad['P_CURRENT']+CLoad['P_IMPEDANCE']+CLoad['P_MVA']
        Load['Q_MVAR'] = CLoad['Q_CURRENT']+CLoad['Q_IMPEDANCE']+CLoad['Q_MVA']
        Loads.append(Load)
    return Loads

def get_switches_info(con):
    CAPE_TIEs = get_Table_Data(con,'BUS_TIE_DATA')
    TIEs = []
    for CTIE in CAPE_TIEs:
        TIE ={}
        TIE['Name'] = CTIE['TIE_NAME'].strip()
        TIE['Tag'] = CTIE['BUS_TIE_TAG']
        TIE['Bus1'] = CTIE['FROM_BUS_NUMBER']
        TIE['Bus2'] = CTIE['TO_BUS_NUMBER']
        
        #TIE['phases'] = CTIE['PHASES']
        #TIE['numPhases'] = len(CTIE['PHASES'])
        TIE['Enabled'] = CTIE['TIE_STATUS'] == 'C'
        TIE["isSwitch"] = True
        TIEs.append(TIE)  
    return TIEs

def get_machine_data(con,Machine_bus):
    MACHINEs = get_Table_Data(con,'MACHINE_DATA')
    machine = [x for x in MACHINEs if MACHINEs['BUS_NUMBER'] == Machine_bus]
    if(len(machine)==0):
        print('\033[93m'+"Warning: No machine fount at bus "+str(Machine_bus)+"\n")
        return []
    else:
        return machine

def get_transformers_info(con,Include_MAGNETIZING=False):
    # n circuit transformers (default)
    nTx_Data = get_Table_Data(con, 'N_CIRCUIT_TRANSFORMER_DATA') # general data
    nTx_Ciruit_cat = get_Table_Data(con,'N_CIRCUIT_TRANSFORMER_CATALOG') # n_circuit transformer MAGNETIZING data 
    Tx_Circuit_data = get_Table_Data(con, 'TRANSFORMER_CIRCUIT_DATA')  # indiviual winding data
    Tx_Circuit_cat = get_Table_Data(con, 'TRANSFORMER_CIRCUIT_CATALOG') # inddividual winding connection info 
    Tx_Z_Mod_Data = get_Table_Data(con,'TRANSFORMER_IMPEDANCE_CATALOG') # Transformer model impedance data
    
    Txs = []
    
    for nTx in nTx_Data:
        Tx = {}
        # general Transforemr data
        Tx['Name'] = nTx['EQUIPMENT_NAME']
        Tx['Tag'] = nTx['TAG']
        Tx['Circuit'] = nTx['CIRCUIT_NUMBER']
        Tx['phases'] = nTx['PHASES']
        Tx['numPhases'] = len(nTx['PHASES'])
        
        # Tags for other Table lookup
        Tx['SUBSTATION_TAG'] = nTx['SUBSTATION_TAG']
        Tx['CATALOG_TAG'] = nTx['CATALOG_TAG']
        
        # terminal data
        Terminals = [x for x in Tx_Circuit_data if x['TRANSFORMER_TAG'] == nTx['TAG']]
        for Term in Terminals:
            if(Term['CIRCUIT'] == 'P'):
                cn = 1
            elif(Term['CIRCUIT'] == 'S'):
                cn = 2
            Tx['Bus'+str(cn)] =  Term['BUS_NUMBER']
            Tx['Bus'+str(cn)+'_kV'] = Term['CIRCUIT_KV']
            Tx['Bus'+str(cn)+'_Ang'] = Term['CIRCUIT_ANGLE'] + Term['IMPLICIT_ANGLE']
            Tx['BUS'+str(cn)+'_BKR_STATUS'] = Term['BKR_STATUS']
            Tx['BUS'+str(cn)+'_Ground'] = Term['NEUTRAL_NODE_NUMBER'] # 0 grounded , -1 ungrounded 
            Tx['Bus'+str(cn)+'_Control'] = Term['CONTROL_TYPE'] # NC no control
            Model_connection = next(x for x in Tx_Circuit_cat if x['CATALOG_TAG'] == Tx['CATALOG_TAG'] and x['CIRCUIT'] == Term['CIRCUIT'])
            match Model_connection['CONNECTION']:
                case 'Y' | 'A':
                    Tx['Bus'+str(cn)+'_CONNECTION'] = 'Y'
                case 'D' | 'O' | 'C' | 'W':
                    Tx['Bus'+str(cn)+'_CONNECTION'] = 'D'
                case 'Z':
                    Tx['Bus'+str(cn)+'_CONNECTION'] = 'Z'
                case _:
                    Tx['Bus'+str(cn)+'_CONNECTION'] = Model_connection['CONNECTION']
        
        Tx['Enabled'] = Tx['BUS1_BKR_STATUS'] == 'C' and Tx['BUS2_BKR_STATUS'] == 'C'
        Tx["isSwitch"] = False
        
        Model_Z = next(x for x in Tx_Z_Mod_Data if x['CATALOG_TAG']==nTx['CATALOG_TAG'])
        Tx['R1pu'] = Model_Z['R1']
        Tx['R0pu'] = Model_Z['R0']
        Tx['X1pu'] = Model_Z['X1']
        Tx['X0pu'] = Model_Z['X0']
        Tx['BASE_MVA'] = Model_Z['BASE_MVA']
        # get magnitizing data usally all zeros 
        Model_Magnetizing = next(x for x in nTx_Ciruit_cat if x['TAG'] == nTx['CATALOG_TAG'])
        Tx['Model'] = Model_Magnetizing['NAME']
        Tx['MANUFACTURER'] = Model_Magnetizing['MANUFACTURER']
        if(Include_MAGNETIZING): 
            Tx['Mag_BASE_MVA'] = Model_Magnetizing['MAGNETIZING_BASE_MVA']
            Tx['Mag_G'] = Model_Magnetizing['MAGNETIZING_G']
            Tx['Mag_B'] = Model_Magnetizing['MAGNETIZING_B']
            Tx['Mag_G0'] = Model_Magnetizing['MAGNETIZING_G0']
            Tx['Mag_B0'] = Model_Magnetizing['MAGNETIZING_B0']
            Tx['Mag_G2'] = Model_Magnetizing['MAGNETIZING_G2']
            Tx['Mag_B2'] = Model_Magnetizing['MAGNETIZING_B2']
        
        # add Tx to list 
        Txs.append(Tx)
    return Txs


    
    

# %% Modify Network 

def set_machine_type(con,Machine_Tag,Type):
    if(Type == 0):
        print("Setting Machine with Tag "+str(Machine_Tag)+" to No Current Limit")
    elif(Type == 1):
        print("Setting Machine with Tag "+str(Machine_Tag)+" to Limit Max 3-phase current")
    elif(Type == 4):
        print("Setting Machine with Tag "+str(Machine_Tag)+" to EPRI IBG (Type IV)")
    elif(Type == 6):
        print("Setting Machine with Tag "+str(Machine_Tag)+" to EPRI IBG (Type III)")
    elif(Type == 7):
        print("Setting Machine with Tag "+str(Machine_Tag)+" to EPRI BESS (Battery Storage)")
    elif(Type == 5):
        print("Setting Machine with Tag "+str(Machine_Tag)+" to Voltage-controlled current source")
    else:
        print('\033[93m'+"Warning: Machine Type "+str(Type)+" not supported ")
        return False
    
    if(Type in [0,1,4,6,7,5]):
        cursor = get_fdb_cursor(con)
        machine_update_str = r'UPDATE machine_data SET USE_CURRENT_LIMIT = '+str(Type)+ r' WHERE TAG = '+str(Machine_Tag)+';'
        cursor.execute(machine_update_str)
        cursor.close()
        con.commit()
        return True
    else:
        return False
    
def add_Bus_to_DB(con,BUS_NUMBER:[int],
                      BUS_NAME:str,
                      BASE_KV:[float],
                      BUS_AREA=0,
                      BUS_ZONE=0,
                      REFERENCE_ANGLE=0,
                      BUS_TYPE='CO',
                      BUS_DESIRED_V_LOW=1,
                      BUS_DESIRED_V_HIGH=1,
                      BUS_VOLTAGE_LIMIT_SET_NUMBER=0,
                      BUS_IN_SERVICE_DATE = None,
                      BUS_OUT_DATE = None,
                      IDE=0,
                      EXTERNAL_BUS_NUMBER=0,
                      BUS_FAULT_RATE=0.0,
                      BUS_PERCENT_SLG=0.0,
                      BUS_PERCENT_DLG=0.0,
                      BUS_PERCENT_TPH=0.0,
                      BUS_PERCENT_LTL=0.0,
                      STATUS_HEX=None,
                      SUBSTATION_TAG=0,
                      PREFAULT_VOLTAGE_MAGNITUDE=1.0,
                      PREFAULT_VOLTAGE_ANGLE=0.0,
                      CHANGED_BY = 'APApy',
                      CHANGED_DATE = 'Now',
                      PARENT_BUS = 0,
                      POSITION_NUMBER=0,
                      EXTERNAL_BUS_NAME=None,
                      STATUS_HEX2=None,
                      OWNER_NUMBER=0,
                      OS_CHANGED_BY=None,
                      OS_CHANGED_DATE=None,
                      BUSBAR_PROTECTION_EXISTS='F',
                      EXTERNAL_BUS_AREA=0,
                      EXTERNAL_BUS_ZONE=0,
                      BES_BUS=None,
                      CIM_RDFID=None,
                      CIM_TERMINAL_RDFID=None,
                      REMARKS=None,
                      PRC_025_POI=None,
                      SQLtest=False):
    
    cursor = get_fdb_cursor(con)
    # check if bus exists
    check_str = r"SELECT * FROM BUS_DATA WHERE BUS_NUMBER = " + str(BUS_NUMBER)
    try:
        cursor.execute(check_str)
    except fdb.Error as e:
        print(f"Error: {e}")
        return -1
    result = cursor.fetchone()
    if(result):
        print('Warning: Bus number allready exists. No changes made to the Database')
        return -2
    #If it dosnet exist insert bus into fdb database 
    cursor.execute("SELECT * From BUS_DATA")
    Tab_Fields = [desc[0] for desc in cursor.description]
    add_bus_str = r"INSERT INTO BUS_DATA ("
    add_bus_str += (", ".join(Tab_Fields) + ') VALUES (')
    values = {}
    for field in Tab_Fields:
        if(locals()[field] is None):
            values[field] = 'NULL'
        else:
            values[field] = str(locals()[field])
            
    for field in Tab_Fields:
        if(field == 'CHANGED_DATE'):
            if(values[field] == 'Now'):
                from datetime import datetime
                values[field] = str(datetime.now())[:-3]
        if(values[field] == 'DEFAULT' or values[field] == 'NULL'):
            add_bus_str += values[field]+","
        else:
            add_bus_str += "'"+values[field]+"',"
    add_bus_str = add_bus_str[:-1] + ")"
    add_bus_str += ";"
    try:
        cursor.execute(add_bus_str)
    except fdb.Error as e:
        print(f"Error: {e}")
        return -1
    cursor.close()
    if(SQLtest):
        print(f"SQL_string to add {BUS_NUMBER} is valid.")
    else:
        con.commit()
        print(f"Added bus {BUS_NAME} to Database wiht bus Number {BUS_NUMBER}")
    return values

class BRANCH_TYPE_List(Enum):
    LINE = 'LINE' # Line 
    CABL = 'CABL' #: Cable,
    CAPA = 'CAPA' #: Series Capacitor,
    REAC = 'REAC' #: Series Reactor,
    LBKR = 'LBKR' #: Load Tap & Breaker,
    SIMP = 'SIMP' #: Simple two-terminal line,
    XFMR = 'XFMR' #: Branch that is part of transformer model,
    EQIV = 'EQIV' #: Equivalent branch from a network reduction,
    EQPS = 'EQPS' #: Equivalent phase-shifter,
    MUTU = 'MUTU' #: Branch created to represent mutual coupling,
    MTER = 'MTER' #: Branch that is part of a multi-terminal line,
    MSEC = 'MSEC' #: A section of a multi-section line,
    FICT = 'FICT' #: Any other form of fictitious branch,

def add_BRANCH_TWO_PORT_MODEL_DATA(con,BRANCH_TAG:[int],
                                   BRANCH_TYPE:[BRANCH_TYPE_List],
                                   R1pu:[float] = None,X1pu:[float] = None,
                                   G1pu:[float] = None,B1pu:[float] = None,
                                   R0pu:[float] = None,X0pu:[float] = None,
                                   G0pu:[float] = None,B0pu:[float] = None,
                                   ZERO_SEQ_ZKM_REAL:[float] = 0,
                                   ZERO_SEQ_ZKM_IMAG:[float] = 0,
                                   ZERO_SEQ_YK_REAL:[float] = 0,
                                   ZERO_SEQ_YK_IMAG:[float] = 0,
                                   ZERO_SEQ_ZMK_REAL:[float] = 0,
                                   ZERO_SEQ_ZMK_IMAG:[float] = 0,
                                   ZERO_SEQ_YM_REAL:[float] = 0,
                                   ZERO_SEQ_YM_IMAG:[float] = 0,
                                   POSITIVE_SEQ_ZKM_REAL:[float] = 0,
                                   POSITIVE_SEQ_ZKM_IMAG:[float] = 0,
                                   POSITIVE_SEQ_YK_REAL:[float] = 0,
                                   POSITIVE_SEQ_YK_IMAG:[float] = 0,
                                   POSITIVE_SEQ_ZMK_REAL:[float] = 0,
                                   POSITIVE_SEQ_ZMK_IMAG:[float] = 0,
                                   POSITIVE_SEQ_YM_REAL:[float] = 0,
                                   POSITIVE_SEQ_YM_IMAG:[float] = 0,
                                   NEGATIVE_SEQ_ZKM_REAL:[float] = 0,
                                   NEGATIVE_SEQ_ZKM_IMAG:[float] = 0,
                                   NEGATIVE_SEQ_YK_REAL:[float] = 0,
                                   NEGATIVE_SEQ_YK_IMAG:[float] = 0,
                                   NEGATIVE_SEQ_ZMK_REAL:[float] = 0,
                                   NEGATIVE_SEQ_ZMK_IMAG:[float] = 0,
                                   NEGATIVE_SEQ_YM_REAL:[float] = 0,
                                   NEGATIVE_SEQ_YM_IMAG:[float] = 0,
                                   MAX_LOAD_CURRENT:[float] = 0.0,
                                   WORST_LOAD_ANGLE:[float] = 0.0,
                                   POS_LINE_CHARGING:[float] = 0.0,
                                   ZERO_LINE_CHARGING:[float] = 0.0,
                                   REFERENCE_DEG_K:[float] = 0,
                                   REFERENCE_DEG_M:[float] = 0,
                                   R1_SCPF:[float] = 0.0,
                                   X1_SCPF:[float] = 0.0,
                                   DATA_STATUS:[str]=None,SQLtest=False):
    if(R0pu):
        ZERO_SEQ_ZKM_REAL = R0pu
        ZERO_SEQ_ZMK_REAL = R0pu
    if(X0pu):
        ZERO_SEQ_ZKM_IMAG = X0pu
        ZERO_SEQ_ZMK_IMAG = X0pu
    if(G0pu):
        ZERO_SEQ_YK_REAL = G0pu/2
        ZERO_SEQ_YM_REAL = G0pu/2
    if(B0pu):
        ZERO_SEQ_YK_IMAG = B0pu/2
        ZERO_SEQ_YM_IMAG = B0pu/2
    if(R1pu):
        POSITIVE_SEQ_ZKM_REAL = R1pu
        POSITIVE_SEQ_ZMK_REAL = R1pu
        NEGATIVE_SEQ_ZKM_IMAG = R1pu
        NEGATIVE_SEQ_ZMK_IMAG = R1pu
    if(X1pu):
        POSITIVE_SEQ_ZKM_IMAG = X1pu
        POSITIVE_SEQ_ZMK_IMAG = X1pu
        NEGATIVE_SEQ_ZKM_IMAG = X1pu
        NEGATIVE_SEQ_ZMK_IMAG = X1pu
    if(G1pu):
        POSITIVE_SEQ_YK_REAL = G1pu/2
        POSITIVE_SEQ_YM_REAL = G1pu/2
        NEGATIVE_SEQ_YK_REAL = G1pu/2
        NEGATIVE_SEQ_YM_REAL = G1pu/2
    if(B1pu):
        POSITIVE_SEQ_YK_IMAG = B1pu/2
        POSITIVE_SEQ_YM_IMAG = B1pu/2
        NEGATIVE_SEQ_YK_IMAG = B1pu/2
        NEGATIVE_SEQ_YM_IMAG = B1pu/2
    
    # check if branch or branch 2 port has Branch Tag
    res_tag2 = r"SELECT * FROM BRANCH_TWO_PORT_MODEL_DATA WHERE BRANCH_TAG = " + str(BRANCH_TAG)
    res1 = check_sql_str(con,res_tag2)
    if(res1):
        print(f"BRANCH TWO PORT MODEL wiht Tag {BRANCH_TAG} allready exists")
        return -2
    
    # add 2 port model 
    cursor = get_fdb_cursor(con)
    cursor.execute("SELECT * From BRANCH_TWO_PORT_MODEL_DATA")
    Tab_Fields = [desc[0] for desc in cursor.description]
    add_B2PM_str = r"INSERT INTO BRANCH_TWO_PORT_MODEL_DATA ("
    add_B2PM_str += (", ".join(Tab_Fields) + ') VALUES (')
    values = {}
    for field in Tab_Fields:
        if(field in locals()):
            if(locals()[field] is None):
                values[field] = 'NULL'
            else:
                values[field] = str(locals()[field])
        else:
            values[field] = 'NULL'
            
    for field in Tab_Fields:
        if(field == 'CHANGED_DATE'):
            if(values[field] == 'Now'):
                from datetime import datetime
                values[field] = str(datetime.now())[:-3]
        if(values[field] == 'DEFAULT' or values[field] == 'NULL'):
            add_B2PM_str += values[field]+","
        else:
            add_B2PM_str += "'"+values[field]+"',"
    add_Line_str = add_B2PM_str[:-1] + ")"
    add_Line_str += ";"
    try:
        cursor.execute(add_Line_str)
    except fdb.Error as e:
        print(f"Error: {e}")
        return -1
    cursor.close()
    if(SQLtest):
        print(f"SQL_string to add Two port model wiht Tag {BRANCH_TAG} is valid.")
    else:
        con.commit()
        print(f"Added Two Port Model {BRANCH_TAG} to Database for Line")
    return values

def add_line_to_DB(con,FROM_BUS_NUMBER,TO_BUS_NUMBER,LINE_LENGTH,LINE_NAME,
                   BRANCH_TAG = None,
                   FROM_BUS_SECTION = None,
                   TO_BUS_SECTION = None,
                   CIRCUIT_NUMBER=1,LINE_AREA=0,LINE_ZONE=0,LINE_AMPACITY=0.0,
                   SURGE_IMP_LOADING=0.0,
                   FROM_BUS_BKR_STATUS='C',TO_BUS_BKR_STATUS='C',
                   FROM_BUS_LOGICAL_BKR_OPER_TIME=0.0,TO_BUS_LOGICAL_BKR_OPER_TIME=0.0,
                   LOSS_BUS = 'T',METER_BUS='F',
                   LINE_IN_SERVICE_DATE=None,LINE_OUT_DATE=None,
                   STATUS_HEX=None,STATUS_HEX2=None,CIRCUIT=None,
                   RATE_1=0.0,RATE_2=0.0,RATE_3=0.0,RATE_4=0.0,RATE_5=0.0,RATE_6=0.0,RATE_7=0.0,RATE_8=0.0,
                   TEMP_RATING_1= 0,TEMP_RATING_2= 0,TEMP_RATING_3= 0,TEMP_RATING_4= 0,
                   TEMP_RATING_5= 0,TEMP_RATING_6= 0,TEMP_RATING_7= 0,TEMP_RATING_8= 0,
                   ST=1,PHASES='ABC',
                   IMPEDANCE_SOURCE = 'M',
                   LIMITING_SECTION_ID = None,
                   LINE_FAULT_RATE = 0.0,
                   LINE_PERCENT_SLG = 0.0,
                   LINE_PERCENT_DLG = 0.0,
                   LINE_PERCENT_TPH = 0.0,
                   LINE_PERCENT_LTL = 0.0,
                   REMARKS = None, UTILITY_ID_NO = None,
                   CHANGED_BY = 'APApy', CHANGED_DATE = 'Now',
                   OS_CHANGED_BY = None, OS_CHANGED_DATE = None,
                   OWNER_NUMBER = 0, OWNER_FRACTION1 = 0.0,
                   OWNER_NUMBER2 = 0, OWNER_FRACTION2 = 0.0,
                   OWNER_NUMBER3 = 0, OWNER_FRACTION3 = 0.0,
                   OWNER_NUMBER4 = 0, OWNER_FRACTION4 = 0.0,
                   CIM_RDFID = None, CIM_FROM_TERMINAL_RDFID = None, CIM_TO_TERMINAL_RDFID = None,
                   BES_EQUIPMENT = 'N',
                   EXTERNAL_BRANCH_ID = None,
                   R1:[float] = None,X1:[float] = None,
                   G1:[float] = None,B1:[float] = None,
                   R0:[float] = None,X0:[float] = None,
                   G0:[float] = None,B0:[float] = None,
                   SQLtest=False,skipB2PMD=False):
    
    # Find next unique Branch Tag
    cursor = get_fdb_cursor(con)
    cursor.execute("SELECT GEN_ID(BRANCH_TAG_GEN, 0) FROM RDB$DATABASE")
    BRANCH_TAG = cursor.fetchone()[0]+1
    print(f"Atempting to add Line wiht TAG {BRANCH_TAG}")
    
    # check if bus exists
    check_Bus1_str1 = r"SELECT * FROM BUS_DATA WHERE BUS_NUMBER = " + str(FROM_BUS_NUMBER)
    check_Bus2_str2 = r"SELECT * FROM BUS_DATA WHERE BUS_NUMBER = " + str(TO_BUS_NUMBER)
    Bus1_real = check_sql_str(con,check_Bus1_str1)
    Bus2_real = check_sql_str(con,check_Bus2_str2)
    if(Bus1_real and Bus2_real):
        pass
    else:
        print(f"Bus {FROM_BUS_NUMBER} or Bus {TO_BUS_NUMBER} not found \n")
        return -1
    
    # check if branch or 
    check_Line_str1 = r"SELECT * FROM LINE_COMMON_DATA WHERE BRANCH_TAG = " + str(BRANCH_TAG)
    check_Line_str2 = f"SELECT * From LINE_COMMON_DATA WHERE LINE_NAME = '{LINE_NAME}' AND FROM_BUS_NUMBER = {FROM_BUS_NUMBER} AND TO_BUS_NUMBER = {TO_BUS_NUMBER}"
    check_B2PDM_str = r"SELECT * FROM BRANCH_TWO_PORT_MODEL_DATA WHERE BRANCH_TAG = " + str(BRANCH_TAG)
    
    Line_in_sys = check_sql_str(con,check_Line_str1)
    Line_in_sys2 = check_sql_str(con,check_Line_str2)
    D2PDM_in_sys = check_sql_str(con,check_B2PDM_str)
    
    if(Line_in_sys or Line_in_sys2):
        print(f"Line {LINE_NAME} with  FROM_BUS_NUMBER = {FROM_BUS_NUMBER}, TO_BUS_NUMBER = {TO_BUS_NUMBER},CIRCUIT_NUMBER = {CIRCUIT_NUMBER} allready exists")
        return -2
    if(D2PDM_in_sys and not skipB2PMD):
        print(f"Branch 2 port model data for tag {BRANCH_TAG} allreday exists")
    
    # Line or branch model dosnt exist add 
    cursor.execute("SELECT * From LINE_COMMON_DATA")
    Tab_Fields = [desc[0] for desc in cursor.description] # get table column names 
    add_Line_str = r"INSERT INTO LINE_COMMON_DATA ("
    add_Line_str += (", ".join(Tab_Fields) + ') VALUES (')
    values = {}
    for field in Tab_Fields:
        if(field in locals()):
            if(locals()[field] is None):
                values[field] = 'NULL'
            else:
                values[field] = str(locals()[field])
        else:
            values[field] = 'NULL'
            
    for field in Tab_Fields:
        if(field == 'CHANGED_DATE'):
            if(values[field] == 'Now'):
                from datetime import datetime
                values[field] = str(datetime.now())[:-3]
        if(values[field] == 'DEFAULT' or values[field] == 'NULL'):
            add_Line_str += values[field]+","
        else:
            add_Line_str += "'"+values[field]+"',"
    add_Line_str = add_Line_str[:-1] + ")"
    add_Line_str += ";"
    try:
        cursor.execute(add_Line_str)
    except fdb.Error as e:
        print(f"Error: {e}")
        return -1
    cursor.close()
    if(SQLtest):
        print(f"SQL_string to add {LINE_NAME} is valid.")
    else:
        con.commit()
        print(f"Added Line {LINE_NAME} between Bus {FROM_BUS_NUMBER} and Bus {TO_BUS_NUMBER} to Database wiht Branch Tag {BRANCH_TAG}")
    #return values
    
    # read waht BRANCH TAG was assigned 
    cursor = get_fdb_cursor(con)
    get_BRANCH_TAG_str = f"SELECT BRANCH_TAG From LINE_COMMON_DATA WHERE FROM_BUS_NUMBER = {FROM_BUS_NUMBER} AND TO_BUS_NUMBER = {TO_BUS_NUMBER} AND CIRCUIT_NUMBER = {CIRCUIT_NUMBER};"
    cursor.execute(get_BRANCH_TAG_str)
    NEW_BRANCH_TAG = cursor.fetchone()[0]
    
    # addtow port model
    if(skipB2PMD==True):
        return [values,0]
    else:
        ret = add_BRANCH_TWO_PORT_MODEL_DATA(con,NEW_BRANCH_TAG,BRANCH_TYPE_List.LINE.value,
                                             R1pu= R1, X1pu = X1, G1pu = G1, B1pu = B1,
                                             R0pu = R0, X0pu = X0, G0pu = G0, B0pu = B0,
                                             SQLtest=SQLtest)
        return [values,ret]

def add_load_to_DB(con,
                   BUS_NUMBER,
                   BRANCH_NAME,                 # Load Name
                   LOAD_NUMBER = 1,             # unique to all shunts at bus 
                   TAG = None,                  # must be unique and assigend by DB
                   BUS_SECTION = None,          # unused
                   ID = None,                   # Load ID 
                   AREA = 0,
                   ZONE = 0,
                   CODE = 'load',               # Key from SHUNT_DATA defines shunt type
                   P = 0,                       # advance load model real power 
                   Q = 0,                       # advance load model reactive power
                   PF_MODEL=0,                  # key from PF_LOAD_MODEL_DATA
                   SC_MODEL=0,                  # key from SC_LOAD_MODEL_DATA
                   TS_MODEL=0,                  # key from TS_LOAD_MODEL_DATA
                   LOGICAL_BKR_OPER_TIME=0.0,   # Breaker operating time
                   IN_SERVICE_DATE=None,
                   OUT_DATE=None,
                   STATUS_HEX=None,
                   STATUS_HEX2=None,
                   REMARKS=None,
                   ST=0,                        # PSS/E status 1:in service 0:out 
                   NEUTRAL_NODE_NUMBER=0,       # 0=solid1y- grounded,-1=ungrounded 
                   P_MVA = 0,                   # constant MVA Load (MVA)
                   Q_MVA = 0,                   # 
                   P_CURRENT = 0,               # constant current Load (MVA)
                   Q_CURRENT = 0,               # 
                   P_IMPEDANCE = 0,             # constant impedance Load (MVA)
                   Q_IMPEDANCE = 0,
                   CHANGED_BY = 'APApy',
                   CHANGED_DATE = 'Now',
                   OS_CHANGED_BY = None,
                   OS_CHANGED_DATE = None,
                   OWNER_NUMBER = 0,            # key from OWNER_DATA
                   CIM_RDFID = None,
                   CIM_TERMINAL_RDFID = None,
                   BES_EQUIPMENT = 'N',
                   PNEG = 0.0,
                   PZERO = 0.0,
                   QNEG = 0.0,
                   QZERO = 0.0,
                   BKR_STATUS = 'C',
                   SQLtest=False):
    
    # Find Next Unique Tag
    cursor = get_fdb_cursor(con)
    cursor.execute("SELECT GEN_ID(SHUNT_TAG_GEN, 0) FROM RDB$DATABASE")
    TAG = cursor.fetchone()[0]+1
    print(f"Atempting to add loda wiht TAG {TAG} at Bus {BUS_NUMBER}")
    
    # check if bus exists
    check_Bus1_str1 = r"SELECT * FROM BUS_DATA WHERE BUS_NUMBER = " + str(BUS_NUMBER)
    Bus1_real = check_sql_str(con,check_Bus1_str1)
    if(Bus1_real):
        pass 
    else:
        print(f"Bus {BUS_NUMBER} not found \n")
        return -1
    
    # check if load nuber is unique
    check_Load_num_str1 = f"SELECT * FROM LOAD_DATA WHERE BUS_NUMBER = {BUS_NUMBER} AND LOAD_NUMBER={LOAD_NUMBER}"
    Load_num_in_use = check_sql_str(con,check_Load_num_str1)
    if(Load_num_in_use):
        print(f"Bus {BUS_NUMBER} allready has a load wiht LOAD_NUMBER={LOAD_NUMBER}")
        return -2
    
    # chekc if Load allready exists 
    check_Load_str1 = f"SELECT * FROM LOAD_DATA WHERE TAG = {TAG} AND BUS_NUMBER = {BUS_NUMBER} AND LOAD_NUMBER={LOAD_NUMBER}"
    Load_in_sys = check_sql_str(con,check_Load_str1)
    if(Load_in_sys):
        print(f"Load {BRANCH_NAME} at  BUS_NUMBER = {BUS_NUMBER} LOAD_NUMBER = {LOAD_NUMBER} allready exists")
        return -2
    
    # Load dosnt exist add 
    cursor.execute("SELECT * From LOAD_DATA")
    Tab_Fields = [desc[0] for desc in cursor.description] # get table column names 
    add_Load_str = r"INSERT INTO LOAD_DATA ("
    add_Load_str += (", ".join(Tab_Fields) + ') VALUES (')
    values = {}
    
    # update code
    cursor.execute("SELECT * From SHUNT_DATA")
    SHUNT_DATA = cursor.fetchall()
    CODE = next(x[0] for x in SHUNT_DATA if x[1].strip().lower() == CODE)
    
    # creat dict of inputs 
    for field in Tab_Fields:
        if(field in locals()):
            if(locals()[field] is None):
                values[field] = 'NULL'
            else:
                values[field] = str(locals()[field])
        else:
            values[field] = 'NULL'
    
    for field in Tab_Fields:
        if(field == 'CHANGED_DATE'):
            if(values[field] == 'Now'):
                from datetime import datetime
                values[field] = str(datetime.now())[:-3]
        if(values[field] == 'DEFAULT' or values[field] == 'NULL'):
            add_Load_str += values[field]+","
        else:
            add_Load_str += "'"+values[field]+"',"
    add_Load_str = add_Load_str[:-1] + ")"
    add_Load_str += ";"
    
    # try and write to DB
    try:
        cursor.execute(add_Load_str)
    except fdb.Error as e:
        print(f"Error: {e}")
        return -1
    cursor.close()
    if(SQLtest):
        print(f"SQL_string to add {BRANCH_NAME} is valid.")
        return values
    else:
        con.commit()
        print(f"Added Load {BRANCH_NAME} at Bus {BUS_NUMBER} to Database wiht Tag: {TAG}")
        return values


# %% Scripting
def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def run_CUPL_script(cape_path,script_abs_path,nogui=False):
    if(nogui):
        cape_command = cape_path + r' /nogui /file:'
    else:
        cape_command = cape_path + r' /file:'
    p = subprocess.Popen(cape_command+script_abs_path, shell = False)
    def killproc():
        print('Reached Killproc\n\n\n\n')
        kill(p.pid)
    
    signal.signal(signal.SIGTERM, killproc)
    print("running "+script_abs_path)
    p.wait()
    return 1
# DB_info = con.db_info([fdb.isc_info_page_size, fdb.isc_info_allocation])



# %% usefull sql info 
# str_gens = "SELECT RDB$GENERATOR_NAME FROM RDB$GENERATORS WHERE RDB$SYSTEM_FLAG = 0;"
# str_trigger_name = "SELECT RDB$TRIGGER_SOURCE FROM RDB$TRIGGERS WHERE RDB$RELATION_NAME = 'BRANCH_TWO_PORT_MODEL_DATA' AND RDB$TRIGGER_TYPE = 1"
# str_contraints = r"SELECT RDB$INDEX_NAME AS CONSTRAINT_NAME, RDB$RELATION_NAME AS TABLE_NAME FROM RDB$INDICES WHERE RDB$RELATION_NAME = 'LOAD_DATA' AND RDB$UNIQUE_FLAG = 1;"
# str_con_cols = r"SELECT RDB$FIELD_NAME FROM RDB$INDEX_SEGMENTS WHERE RDB$INDEX_NAME = 'LOAD_NUM_COMP' ORDER BY RDB$FIELD_POSITION;"
# str_check_index_tabs = r"SELECT ind.RDB$RELATION_NAME AS TABLE_NAME, seg.RDB$FIELD_NAME AS COLUMN_NAME, seg.RDB$FIELD_POSITION + 1 AS POSITION_IN_INDEX FROM RDB$INDEX_SEGMENTS seg JOIN RDB$INDICES ind ON seg.RDB$INDEX_NAME = ind.RDB$INDEX_NAME WHERE ind.RDB$INDEX_NAME = 'LOAD_NUM_COMP' ORDER BY seg.RDB$FIELD_POSITION;"

