import os

def write_short_circuit_script(script_files,script_file_name,
                               capedbloc,
                               Fault_buses,Fault_Res,Fault_types,
                               Result_File,
                               header = True,
                               capeGFloc=None,
                               ACC_Factor=None,
                               recorder_LOCarray=[],
                               record_IBRstatus=[],
                               record_FaultBus=True,
                               closeAPA=True):
    """Generate an ASPEN OneLiner/APA short-circuit macro script (.mac) for fault simulations.

    This function writes a CUPL/APA macro file that:
      1) Attaches an APA database,
      2) Builds the short-circuit network and enters the SC module,
      3) Defines helper macros to apply a bus fault and report results,
      4) Optionally configures MXI acceleration factors,
      5) Runs a set of faults (by type and impedance) across a specified bus set,
      6) Writes results to an APA report file and optionally terminates APA.

    The generated script prints one CSV-like line per simulated condition to the APA report
    (and/or screen, depending on APA settings). The first columns identify the fault bus,
    relay/measurement point, fault impedance, and fault type; remaining columns contain
    magnitudes/angles for phase and sequence currents/voltages, plus solver iteration count
    (``MXI_TOTAL_ITER``).

    Notes:
      - The output macro filename is forced to end with ``_1.mac`` and will overwrite any
        existing file with the same name in ``script_files``.
      - Only fault types in ``['ABC', 'AG', 'BC', 'BCG']`` are supported by the generated macro.

    Args:
      script_files: Directory path where the macro should be written.
        This is concatenated directly with the filename; ensure it includes a trailing
        path separator (e.g., ``"C:/tmp/"``) to avoid malformed paths.
      script_file_name: Base filename for the macro. The function strips the extension
        (if any) and appends ``_1.mac``.
      capedbloc: Path to the APA database (DB) to open via ``ready_db``.
      Fault_buses: Iterable of bus numbers to include in the APA bus set ``faultbusset``.
      Fault_Res: Iterable of fault impedances. Each element is expected to behave like a
        complex number with ``.real`` (R) and ``.imag`` (X) parts.
      Fault_types: Iterable of fault type strings. Supported values: ``'ABC'``, ``'AG'``,
        ``'BC'``, ``'BCG'``.
      Result_File: Output path for APA ``report`` (the generated script calls ``report "..."``).
      header: If True, writes a CSV header line to the report before running faults.
      capeGFloc: Optional path to a drawing/graphics file to load via ``Read_Drawing``.
      ACC_Factor: Optional MXI accelerator configuration. Accepted formats:
        - float: enables EPRI Type IV constant accelerator factor.
        - list of two floats: enables EPRI Type IV adaptive range [min, max].
        - dict: per-model configuration, keys may include ``'VCCS'``, ``'EPRI_Type_IV'``,
          ``'EPRI_Type_III'``, ``'BESS'``; each value may be float (constant) or
          [min, max] list (adaptive). Values are clamped to [0.01, 1.0] and rounded to 0.01.
      recorder_LOCarray: Optional list of recorder definitions for line/branch measurements.
        Each element should be a dict with keys: ``'Bus1'``, ``'Bus2'``, ``'Circuit'``, and
        either ``'Name'`` or ``'Tag'``. When provided, the script records currents/voltages
        at these locations during each fault.
      record_IBRstatus: Optional list of bus numbers for which to record
        ``MXI_SHUNT_STATUS <bus> 0 1`` during each fault.
      record_FaultBus: If True, records phase and sequence currents/voltages at the faulted bus.
      closeAPA: If True, the generated script ends with ``terminate`` to close APA.

    Returns:
      Absolute (constructed) path to the generated macro script file.

    Raises:
      None explicitly. On some invalid ``ACC_Factor`` formats, the function prints an error and
      returns ``-1`` early (legacy behavior), otherwise file I/O errors may propagate.

    """
    
    # if previous version of script exist remove it 
    script_file = os.path.splitext(script_file_name)[0]
    if os.path.isfile(script_files+script_file+'_1.mac') :
        os.remove(script_files+script_file+'_1.mac')
        
    # open file and write CUPL code 
    script_abs_path = script_files+script_file+'_1.mac'
    g = open(script_files+script_file+'_1.mac','w+')
    
    # write fault macro in CUPL
    strFaultSimMacro = ("echo OFF\n")
    strFaultSimMacro += ("log_echo OFF\n\n")
    
    # Define a macro that creates a named fault, applies it, reports results, then deletes it.
    # Macro inputs:
    #   $1: Fault resistance (string)
    #   $2: Fault type string (one of ABC, AG, BC, BCG)
    #   $3: Bus set name (e.g., faultbusset)
    #   $4: Fault reactance (string)
    strFaultSimMacro += ("define_macro(fault_sim_py,\n")
    if(len(recorder_LOCarray)>0):
        strFaultSimMacro += ("\trelay_locs\n")
        
    strFaultSimMacro += ("\treport_header off\n")
    strFaultSimMacro += ("\tsave 'py_fault' as fault_name\n\tsave strcat(\"delete_fault \",fault_name) str1\n\tstr1\n")
    strFaultSimMacro += ("\tIF ($2 = \"ABC\") THEN\n\t\tsave strcat(\"define_fault \",fault_name,\" 1 1A 0 \",$1,\" \",$4,\" 0 0 1B 0 \",$1,\" \",$4,\" 0 0 1C 0 \",$1,\" \",$4,\" 0 0 x\") as str2\n")
    strFaultSimMacro += ("\tELSEIF 	($2 = \"AG\") THEN\n\t\tsave strcat(\"define_fault \",fault_name,\" 1 1A 0 \",$1,\" \",$4,\" 0 0 x\") as str2\n")
    strFaultSimMacro += ("\tELSEIF 	($2 = \"BC\") THEN\n\t\tsave strcat(\"define_fault \",fault_name,\" 1 1B 1C \",$1,\" \",$4,\" 0 0 x\") as str2\n")
    strFaultSimMacro += ("\tELSEIF 	($2 = \"BCG\") THEN\n\t\tsave strcat(\"define_fault \",fault_name,\" 1 1B 0 \",$1,\" \",$4,\" 0 0 1C 0 \",$1,\" \",$4,\" 0 0 x\") as str2\n")
    strFaultSimMacro += ("\tELSE\n\t\tDISPLAY 'Error: Fault Type not supported.'\n\t\tBREAK\n\tENDIF\n\n\tstr2\n\tapply_bus_fault_and_report($1,$2,$3,$4)\n\tstr1\n)\n\n")
    g.write(strFaultSimMacro)
    
    # Define a macro that loops over buses in the bus set, applies the fault, and reports.
    g.write("ma(apply_bus_fault_and_report,\n")       # create function that simulates fault 
    g.write("\tsave ',' as sep_char\n")               # set , as a seperator for the result file 
    g.write("\tIF ($4 = '0.0') THEN\n\t\tsave $1 as fault_RX\n")
    g.write("\tELSEIF  ($4(1:1)='-') THEN\n\t\tsave strcat($1,$4,'j') as fault_RX\n")
    g.write("\tELSE\n\t\tsave strcat($1,'+',$4,'j') as fault_RX\n\tENDIF\n\n")
    
    
    g.write("\tdobuses(faultbusset,\n")               # loop over buses in faultbusset defined earlier, start do buses loop
    g.write("\t\tsave #k as busnum\n")                # set k as bus number from faultbusset
    g.write("\t\taf fault_name busnum x\n")           # run fault named fault_name defined earlier on bus number k  
    
    # decide what to record and where.
    
    # Optionally record fault-bus phase and sequence currents/voltages (always at the faulted bus).
    if(record_FaultBus):
        # get fault Ia,Ib,Ic
        g.write("\t\tsave (IFA*baseamps) busnum as I_aF\n\t\tsave abs(I_aF) as Ia_mag\n\t\tsave arg(I_aF) as Ia_ang\n\n")
        g.write("\t\tsave (IFB*baseamps) busnum as I_bF\n\t\tsave abs(I_bF) as Ib_mag\n\t\tsave arg(I_bF) as Ib_ang\n\n")
        g.write("\t\tsave (IFC*baseamps) busnum as I_cF\n\t\tsave abs(I_cF) as Ic_mag\n\t\tsave arg(I_cF) as Ic_ang\n\n")
        # get fault bus Va,Vb,Vc
        g.write("\t\tsave (VA) busnum as V_aF\n\t\tsave abs(V_aF) as Va_mag\n\t\tsave arg(V_aF) as Va_ang\n\n")
        g.write("\t\tsave (VB) busnum as V_bF\n\t\tsave abs(V_bF) as Vb_mag\n\t\tsave arg(V_bF) as Vb_ang\n\n")
        g.write("\t\tsave (VC) busnum as V_cF\n\t\tsave abs(V_cF) as Vc_mag\n\t\tsave arg(V_cF) as Vc_ang\n\n")
        # record sequecne curretns I0,I1,I2
        g.write("\t\t\tsave (IFZ * baseamps) busnum as IRESF\n\t\t\tsave abs(IRESF) as IRES_mag\n\t\t\tsave arg(IRESF) as IRES_ang\n\n")
        g.write("\t\t\tsave (IFP * baseamps) busnum as I_PF\n\t\t\tsave abs(I_PF) as IP_mag\n\t\t\tsave arg(I_PF) as IP_ang\n\n")
        g.write("\t\t\tsave (IFN * baseamps) busnum as I_NF\n\t\t\tsave abs(I_NF) as IN_mag\n\t\t\tsave arg(I_NF) as IN_ang\n\n")
        # recored sequence voltage V0,V1,V2
        g.write("\t\t\tsave (VZ) busnum as V_ZF\n\t\t\tsave abs(V_ZF) as VZ_mag\n\t\t\tsave arg(V_ZF) as VZ_ang\n\n")
        g.write("\t\t\tsave (VP) busnum as V_PF\n\t\t\tsave abs(V_PF) as VP_mag\n\t\t\tsave arg(V_PF) as VP_ang\n\n")
        g.write("\t\t\tsave (VN) busnum as V_NF\n\t\t\tsave abs(V_NF) as VN_mag\n\t\t\tsave arg(V_NF) as VN_ang\n\n")

        # combine and write to file
        g.write("\t\tsave strcat(ntoa(busnum),sep_char,'Fault',sep_char,fault_RX,sep_char,$2,sep_char, ntoa(Ia_mag), sep_char, ntoa(Ia_ang), sep_char,ntoa(Ib_mag), sep_char,ntoa(Ib_ang), sep_char,ntoa(Ic_mag), sep_char,ntoa(Ic_ang)) as strIFabc\n")
        g.write("\t\tsave strcat(sep_char,ntoa(Va_mag), sep_char,ntoa(Va_ang),sep_char,ntoa(Vb_mag), sep_char,ntoa(Vb_ang), sep_char,ntoa(Vc_mag),sep_char,ntoa(Vc_ang)) as strVFabc\n")
        g.write("\t\t\tsave strcat(sep_char,ntoa(IRES_mag,\"F0.4\"),sep_char,ntoa(IRES_ang,\"F0.4\"),sep_char,ntoa(IP_mag,\"F0.4\"),sep_char,ntoa(IP_ang,\"F0.4\"),sep_char,ntoa(IN_mag,\"F0.4\"),sep_char,ntoa(IN_ang,\"F0.4\")) as strIF012\n")                
        g.write("\t\t\tsave strcat(sep_char,ntoa(VZ_mag,\"F0.4\"),sep_char,ntoa(VZ_ang,\"F0.4\"),sep_char,ntoa(VP_mag,\"F0.4\"), sep_char,ntoa(VP_ang,\"F0.4\"), sep_char,ntoa(VN_mag,\"F0.4\"),sep_char,ntoa(VN_ang,\"F0.4\")) as strVF012\n")
        g.write("\t\t\tsave strcat(strIFabc,strVFabc,strIF012,strVF012,sep_char,ntoa(MXI_TOTAL_ITER)) as strFVIs\n\n")
        g.write("\t\tdisplay strFVIs\n\n")
    
    # Optionally query and report IBR status for specified buses,breaks the csv fault format.
    if(len(record_IBRstatus)>0):
        for IBR_bus in record_IBRstatus:
            g.write("\t\tsave MXI_SHUNT_STATUS "+str(IBR_bus)+" 0 1 as strIBR_"+str(IBR_bus)+"\n")
            g.write("\t\tsave strcat(ntoa(busnum),sep_char,'MXI_"+str(IBR_bus)+"',sep_char,fault_RX,sep_char,$2,sep_char,strIBR_"+str(IBR_bus)+"(1:65)) as IBRst"+str(IBR_bus)+"\n")
            g.write("\t\tdisplay  IBRst"+str(IBR_bus)+"\n")
    
    # Optionally record currents/voltages at specified relay/branch locations during each fault.
    if(len(recorder_LOCarray)>0):
        g.write("\t\tsave 1 as i\n")
        g.write("\t\tdowhile(i<"+str(len(recorder_LOCarray)+1)+",\n") # clsoe dowhile loop
        
        # recored curretns  Ia,Ib,IC 
        g.write("\t\t\tsave (Ia*baseamps) from_bus(i) to_bus(i) circuit_n(i) as I_a\n\t\t\tsave abs(I_a) as Ia_mag\n\t\t\tsave arg(I_a) as Ia_ang\n\n")
        g.write("\t\t\tsave (Ib*baseamps) from_bus(i) to_bus(i) circuit_n(i) as I_b\n\t\t\tsave abs(I_b) as Ib_mag\n\t\t\tsave arg(I_b) as Ib_ang\n\n")
        g.write("\t\t\tsave (Ic*baseamps) from_bus(i) to_bus(i) circuit_n(i) as I_c\n\t\t\tsave abs(I_c) as Ic_mag\n\t\t\tsave arg(I_c) as Ic_ang\n\n")
        
        # recored voltages at from bus Va,Vb,Vc
        g.write("\t\t\tsave (VA) from_bus(i) as V_a\n\t\t\tsave abs(V_a) as Va_mag\n\t\t\tsave arg(V_a) as Va_ang\n\n")
        g.write("\t\t\tsave (VB) from_bus(i) as V_b\n\t\t\tsave abs(V_b) as Vb_mag\n\t\t\tsave arg(V_b) as Vb_ang\n\n")
        g.write("\t\t\tsave (VC) from_bus(i) as V_c\n\t\t\tsave abs(V_c) as Vc_mag\n\t\t\tsave arg(V_c) as Vc_ang\n\n")
        
        # record sequecne curretns I0,I1,I2
        g.write("\t\t\tsave (IZ * baseamps) from_bus(i) to_bus(i) circuit_n(i) AS IRES\n\t\t\tsave abs(IRES) as IRES_mag\n\t\t\tsave arg(IRES) as IRES_ang\n\n")
        g.write("\t\t\tsave (IP * baseamps) from_bus(i) to_bus(i) circuit_n(i) AS I_P\n\t\t\tsave abs(I_P) as IP_mag\n\t\t\tsave arg(I_P) as IP_ang\n\n")
        g.write("\t\t\tsave (IN * baseamps) from_bus(i) to_bus(i) circuit_n(i) AS I_N\n\t\t\tsave abs(I_N) as IN_mag\n\t\t\tsave arg(I_N) as IN_ang\n\n")
        
        # recored sequence voltage V0,V1,V2
        g.write("\t\t\tsave (VZ) from_bus(i) as V_Z\n\t\t\tsave abs(V_Z) as VZ_mag\n\t\t\tsave arg(V_Z) as VZ_ang\n\n")
        g.write("\t\t\tsave (VP) from_bus(i) as V_P\n\t\t\tsave abs(V_P) as VP_mag\n\t\t\tsave arg(V_P) as VP_ang\n\n")
        g.write("\t\t\tsave (VN) from_bus(i) as V_N\n\t\t\tsave abs(V_N) as VN_mag\n\t\t\tsave arg(V_N) as VN_ang\n\n")
        
        # write to recored VIs to file 
        g.write("\t\t\tsave strcat(ntoa(busnum),sep_char,relay_n(i),sep_char,fault_RX,sep_char,$2,sep_char, ntoa(Ia_mag), sep_char, ntoa(Ia_ang), sep_char,ntoa(Ib_mag), sep_char,ntoa(Ib_ang), sep_char,ntoa(Ic_mag), sep_char,ntoa(Ic_ang)) as strIabc\n")
        g.write("\t\t\tsave strcat(sep_char,ntoa(Va_mag,\"F0.4\"), sep_char,ntoa(Va_ang,\"F0.4\"),sep_char,ntoa(Vb_mag,\"F0.4\"), sep_char,ntoa(Vb_ang,\"F0.4\"), sep_char,ntoa(Vc_mag,\"F0.4\"),sep_char,ntoa(Vc_ang,\"F0.4\")) as strVabc\n")
        g.write("\t\t\tsave strcat(sep_char,ntoa(IRES_mag,\"F0.4\"),sep_char,ntoa(IRES_ang,\"F0.4\"),sep_char,ntoa(IP_mag,\"F0.4\"),sep_char,ntoa(IP_ang,\"F0.4\"),sep_char,ntoa(IN_mag,\"F0.4\"),sep_char,ntoa(IN_ang,\"F0.4\")) as strI012\n")                
        g.write("\t\t\tsave strcat(sep_char,ntoa(VZ_mag,\"F0.4\"),sep_char,ntoa(VZ_ang,\"F0.4\"),sep_char,ntoa(VP_mag,\"F0.4\"), sep_char,ntoa(VP_ang,\"F0.4\"), sep_char,ntoa(VN_mag,\"F0.4\"),sep_char,ntoa(VN_ang,\"F0.4\")) as strV012\n")
        g.write("\t\t\tsave strcat(strIabc,strVabc,strI012,strV012,sep_char,ntoa(MXI_TOTAL_ITER)) as strVIs\n\n")
        g.write("\t\t\tdisplay  strVIs\n\n")
        # incriment to next recoreder
        g.write("\t\t\tsave (i + 1) as i\n\n")
        g.write("\t\t)\n") # clsoe dowhile loop
    
    g.write("\t)\n") # clsoe do buses loop
    g.write(")\n") # clsoe function
    
    # If relay recoreder are provided, define arrays holding each monitored branch and label.
    if(len(recorder_LOCarray)>0):
        g.write("ma( relay_locs,\n")
        g.write("\tdefine_array from_bus\n\tdefine_array to_bus\n\tdefine_array circuit_n\n\tdefine_array relay_n\n\n")
        ii=1
        for rec in recorder_LOCarray:
            g.write("\tsave "+str(rec['Bus1'])+" as from_bus("+str(ii)+")\n")
            g.write("\tsave "+str(rec['Bus2'])+" as to_bus("+str(ii)+")\n")
            g.write("\tsave "+str(rec['Circuit'])+" as circuit_n("+str(ii)+")\n")
            # Prefer relay Name if present; otherwise use Tag.
            if(len(rec['Name'].strip()) > 0 ):
                g.write("\tsave '"+str(rec['Name'])+"' as relay_n("+str(ii)+")\n\n")
            else:
                g.write("\tsave '"+str(rec['Tag'])+"' as relay_n("+str(ii)+")\n\n")
            ii+=1
        g.write(")\n")
    
    # Configure APA environment: disable screen reports, open DB, optionally read drawing,
    # build SC network, switch to SC module, and request current reporting modes.
    g.write('\n\nscreen_reports OFF\n') # dissable screen reporting 
    g.write('ready_db "'+capedbloc+'"\n') # attach database to APA (ned to figure out how to set with/without PF)
    if(capeGFloc):
        g.write('Read_Drawing "'+capeGFloc+'"\n')
    g.write("build_sc_network\n")   
    g.write("sc\n") # switch to SC module
    g.write("REPORTED_CURRENTS TOTAL x\n")
    g.write("RELAY_CURRENTS TOTAL x\n")
    
    # Optionally configure MXI accelerator factors (with clamping and rounding). 
    if(ACC_Factor):
        max_acc = 1.0
        min_acc = 0.01
        # Default behavior: EPRI Type IV unless a dict specifies otherwise.
        if(type(ACC_Factor) is float):
            ACC_Factor = max(min_acc, min(round(ACC_Factor,2), max_acc))
            g.write("MXI_EPRI_IV_ACCEL_CONSTANT On\n")
            g.write("MXI_ACCELERATOR_FACTOR "+str(ACC_Factor)+" \n")
        elif(type(ACC_Factor) is list):
            ACC_Factor[0] = max(min_acc, min(round(ACC_Factor[0],2), max_acc))
            ACC_Factor[1] = max(min_acc, min(round(ACC_Factor[1],2), max_acc))
            g.write("MXI_EPRI_IV_ACCEL_CONSTANT Off\n")
            g.write("MXI_ACCELERATOR_FACTOR_ADAP_MIN " + str(ACC_Factor[0])+" \n")
            g.write("MXI_ACCELERATOR_FACTOR_ADAP_MAX " + str(ACC_Factor[1])+" \n")
        
        # Supply all types as a dict for per-model configuration.
        elif(type(ACC_Factor) is dict):
            for acc_key in ACC_Factor.keys():
                # Check and limit to within 0.01 to 1.0 in steps of 0.01.
                if(type(ACC_Factor[acc_key]) is float):
                    ACC_Factor[acc_key] = max(min_acc, min(round(ACC_Factor[acc_key],2), max_acc))
                elif(type(ACC_Factor[acc_key]) is list):
                    ACC_Factor[acc_key][0] = max(min_acc, min(round(ACC_Factor[acc_key][0],2), max_acc))
                    ACC_Factor[acc_key][1] = max(min_acc, min(round(ACC_Factor[acc_key][1],2), max_acc))
                else:
                    print("Error:incorrect ACC Factor format\n")
                    return -1
                
                if(acc_key =='VCCS'):
                # VCCS acc factor settings 
                    if(type(ACC_Factor[acc_key]) is float):
                        g.write( "MXI_VCCS_ACCEL_CONSTANT On\nMXI_ACCELERATOR_FACTOR_VCCS " + str(ACC_Factor[acc_key])+" \n")
                    elif(type(ACC_Factor[acc_key]) is list):
                        g.write("MXI_VCCS_ACCEL_CONSTANT Off\n")
                        g.write("MXI_ACCELERATOR_FACTOR_VCCS_ADAP_MIN " + str(ACC_Factor[acc_key][0])+" \n")
                        g.write("MXI_ACCELERATOR_FACTOR_VCCS_ADAP_MAX " + str(ACC_Factor[acc_key][1])+" \n")
                    else:
                        print("Error:incorrect ACC Factor format\n")
                        return -1
                # Type IV acc factor settings
                elif(acc_key == 'EPRI_Type_IV'):
                    if(type(ACC_Factor[acc_key]) is float):
                        g.write( "MXI_EPRI_IV_ACCEL_CONSTANT On\nMXI_ACCELERATOR_FACTOR " + str(ACC_Factor[acc_key])+" \n")
                    elif(type(ACC_Factor[acc_key]) is list):
                        g.write("MXI_EPRI_IV_ACCEL_CONSTANT Off\n")
                        g.write("MXI_ACCELERATOR_FACTOR_ADAP_MIN " + str(ACC_Factor[acc_key][0])+" \n")
                        g.write("MXI_ACCELERATOR_FACTOR_ADAP_MAX " + str(ACC_Factor[acc_key][1])+" \n")
                    else:
                        print("Error:incorrect ACC Factor format\n")
                        return -1
                # Type III acc factor settings
                elif(acc_key == 'EPRI_Type_III'):
                    if(type(ACC_Factor[acc_key]) is float):
                        g.write( "MXI_EPRI_III_ACCEL_CONSTANT On\nMXI_ACCELERATOR_FACTOR_EPRI_III " + str(ACC_Factor[acc_key])+" \n")
                    elif(type(ACC_Factor[acc_key]) is list):
                        g.write("MXI_EPRI_III_ACCEL_CONSTANT Off\n")
                        g.write("MXI_ACCELERATOR_FACTOR_EPRI_III_ADAP_MIN " + str(ACC_Factor[acc_key][0])+" \n")
                        g.write("MXI_ACCELERATOR_FACTOR_EPRI_III_ADAP_MAX " + str(ACC_Factor[acc_key][1])+" \n")
                    else:
                        print("Error:incorrect ACC Factor format\n")
                        return -1
                # BESS acc factor settings
                elif(acc_key == 'BESS'):
                    if(type(ACC_Factor[acc_key]) is float):
                        g.write( "MXI_BESS_ACCEL_CONSTANT On\nMXI_ACCELERATOR_FACTOR_EPRI_III " + str(ACC_Factor[acc_key])+" \n")
                    elif(type(ACC_Factor[acc_key]) is list):
                        g.write("MXI_BESS_ACCEL_CONSTANT Off\n")
                        g.write("MXI_ACCELERATOR_FACTOR_BESS_ADAP_MIN " + str(ACC_Factor[acc_key][0])+" \n")
                        g.write("MXI_ACCELERATOR_FACTOR_BESS_ADAP_MAX " + str(ACC_Factor[acc_key][1])+" \n")
                    else:
                        print("Error:incorrect ACC Factor format\n")
                        return -1
                else:
                    # Unknown types are skipped.
                    print("Error: Unknown ACC Factor type "+ str(acc_key)+", skipping to next key\n")
                    
    # turn screen reporting off and set the report path.
    g.write("screen_reports OFF\n")
    # write result file location 
    g.write("report \""+Result_File+"\"\n")
    
    # Define a bus set in APA containing all fault buses.
    dbs_str = "dbs(faultbusset, number = "
    for bus in Fault_buses:
        if(Fault_buses[0] == bus):
            dbs_str = dbs_str + str(bus)
        else:
            dbs_str = dbs_str + ','+str(bus)
    g.write(dbs_str+')\n')
    
    # Optionally write a CSV header line (must match the data columns produced above). # broken ned to find workaround
    if(header):
        g.write("display \"Fault_Bus,Relay,Fault_Z,Fault_Type,Ia_mag,Ia_ang,Ib_mag,Ib_ang,Ic_mag,Ic_ang,Va_mag,Va_ang,Vb_mag,Vb_ang,Vc_mag,Vc_ang,I0_mag,I0_ang,I1_mag,I1_ang,I2_mag,I2_ang,V0_mag,V0_ang,V1_mag,V1_ang,V2_mag,V2_ang,conv\" \n")
    
    # Write macro calls for each requested fault type and each requested fault impedance.
    for Fault_type in Fault_types:
        if(Fault_type in ['ABC','AG','BC','BCG']):
            for Fault_R in Fault_Res:
                g.write("fault_sim_py('"+str(Fault_R.real)+"',\""+Fault_type+"\",faultbusset,'"+str(Fault_R.imag)+"')\n")
        else:
            # Unsupported fault types are not written to the script.
            print ('Error: Fault type {} not supported'.format(Fault_type))
            
    # Clear fault bus set
    g.write("erset faultbusset\n")
    # save repoer
    g.write("save_report\n")
    
    # Optionally terminate APA at the end of the script.
    g.write("screen_reports ON\n")
    if(closeAPA):
        g.write("terminate\n")
    g.close()
    
    return script_abs_path