import os


def write_short_circuit_script(cape_path,
                               script_files,script_file_name,
                               capedbloc,
                               Fault_buses,Fault_Res,Fault_types,
                               Result_File,
                               capeGFloc=None,
                               ACC_Factor=None,
                               recorder_LOCarray=[],
                               record_IBRstatus=[],
                               record_FaultBus=True,
                               closeAPA=True):
    
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
    
    #write fault sim macro that simualtes fautls 
    # macro inputs: fault resitacne as a string, 
    #               fault type as a supported string (only one type at a time),
    #               fult bus set as a saved bus set
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
    
    # write fault simulation and recorder fuction
    g.write("ma(apply_bus_fault_and_report,\n")       # create function that simulates fault 
    g.write("\tsave ',' as sep_char\n")               # set , as a seperator for the result file 
    g.write("\tIF ($4 = '0.0') THEN\n\t\tsave $1 as fault_RX\n")
    g.write("\tELSEIF  ($4(1:1)='-') THEN\n\t\tsave strcat($1,$4,'j') as fault_RX\n")
    g.write("\tELSE\n\t\tsave strcat($1,'+',$4,'j') as fault_RX\n\tENDIF\n\n")
    
    
    g.write("\tdobuses(faultbusset,\n")               # loop over buses in faultbusset defined earlier, start do buses loop
    g.write("\t\tsave #k as busnum\n")                # set k as bus number from faultbusset
    g.write("\t\taf fault_name busnum x\n")           # run fault named fault_name defined earlier on bus number k  
    
        # decide what to record and where. Fault recoreder will allwasys recore Ia,Ib,Ic,Va,Vb,Vc 
    if(record_FaultBus):
        # get fault Ia,Ib,Ic
        g.write("\t\tsave (IFA*baseamps) busnum as I_aF\n\t\tsave abs(I_aF) as Ia_mag\n\t\tsave arg(I_aF) as Ia_ang\n\n")
        g.write("\t\tsave (IFB*baseamps) busnum as I_bF\n\t\tsave abs(I_bF) as Ib_mag\n\t\tsave arg(I_bF) as Ib_ang\n\n")
        g.write("\t\tsave (IFC*baseamps) busnum as I_cF\n\t\tsave abs(I_cF) as Ic_mag\n\t\tsave arg(I_cF) as Ic_ang\n\n")
        # get fault bus Va,Vb,Vc
        g.write("\t\tsave (VA) busnum as V_aF\n\t\tsave abs(V_aF) as Va_mag\n\t\tsave arg(V_aF) as Va_ang\n\n")
        g.write("\t\tsave (VB) busnum as V_bF\n\t\tsave abs(V_bF) as Vb_mag\n\t\tsave arg(V_bF) as Vb_ang\n\n")
        g.write("\t\tsave (VC) busnum as V_cF\n\t\tsave abs(V_cF) as Vc_mag\n\t\tsave arg(V_cF) as Vc_ang\n\n")
        
        #g.write("\t\tsave 'Fault' as relay_F")
        
        g.write("\t\tsave strcat(ntoa(busnum),sep_char,'Fault',sep_char,fault_RX,sep_char,$2,sep_char, ntoa(Ia_mag), sep_char, ntoa(Ia_ang), sep_char,ntoa(Ib_mag), sep_char,ntoa(Ib_ang), sep_char,ntoa(Ic_mag), sep_char,ntoa(Ic_ang)) as strIFabc\n")
        g.write("\t\tsave strcat(sep_char,ntoa(Va_mag), sep_char,ntoa(Va_ang),sep_char,ntoa(Vb_mag), sep_char,ntoa(Vb_ang), sep_char,ntoa(Vc_mag),sep_char,ntoa(Vc_ang)) as strVFabc\n")
        g.write("\t\tsave strcat(strIFabc,strVFabc,sep_char,ntoa(MXI_TOTAL_ITER)) as strFVIs\n")
        g.write("\t\tdisplay strFVIs\n\n")
        
    if(len(record_IBRstatus)>0):
        for IBR_bus in record_IBRstatus:
            g.write("\t\tsave MXI_SHUNT_STATUS "+str(IBR_bus)+" 0 1 as strIBR_"+str(IBR_bus)+"\n")
            g.write("\t\tsave strcat(ntoa(busnum),sep_char,'MXI_"+str(IBR_bus)+"',sep_char,fault_RX,sep_char,$2,sep_char,strIBR_"+str(IBR_bus)+"(1:65)) as IBRst"+str(IBR_bus)+"\n")
            g.write("\t\tdisplay  IBRst"+str(IBR_bus)+"\n")
            
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
        g.write("\t\t\tsave (3 * IZ* baseamps) from_bus(i) to_bus(i) circuit_n(i) AS IRES\n\t\t\tsave abs(IRES) as IRES_mag\n\t\t\tsave arg(IRES) as IRES_ang\n\n")
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
    
    # create list of recorders
    if(len(recorder_LOCarray)>0):
        g.write("ma( relay_locs,\n")
        g.write("\tdefine_array from_bus\n\tdefine_array to_bus\n\tdefine_array circuit_n\n\tdefine_array relay_n\n\n")
        ii=1
        for rec in recorder_LOCarray:
            g.write("\tsave "+str(rec['Bus1'])+" as from_bus("+str(ii)+")\n")
            g.write("\tsave "+str(rec['Bus2'])+" as to_bus("+str(ii)+")\n")
            g.write("\tsave "+str(rec['Circuit'])+" as circuit_n("+str(ii)+")\n")
            if(len(rec['Name'].strip()) > 0 ):
                g.write("\tsave '"+str(rec['Name'])+"' as relay_n("+str(ii)+")\n\n")
            else:
                g.write("\tsave '"+str(rec['Tag'])+"' as relay_n("+str(ii)+")\n\n")
            ii+=1
        g.write(")\n")
    
    g.write('\n\nscreen_reports OFF\n') # dissable screen reporting 
    g.write('ready_db "'+capedbloc+'"\n') # attach database to APA (ned to figure out how to set with/without PF)
    if(capeGFloc):
        g.write('Read_Drawing "'+capeGFloc+'"\n')
    g.write("build_sc_network\n")   
    g.write("sc\n") # switch to SC module
    g.write("REPORTED_CURRENTS TOTAL x\n")
    g.write("RELAY_CURRENTS TOTAL x\n")
    
    # set acc factors 
    if(ACC_Factor):
        g.write("MXI_EPRI_IV_ACCEL_CONSTANT On\n")
        g.write("MXI_ACCELERATOR_FACTOR "+str(ACC_Factor)+" \n")
    
    g.write("screen_reports OFF\n")
    # write result file location 
    g.write("report \""+Result_File+"\"\n")
    
    # write what buses to simulate fautls on
    dbs_str = "dbs(faultbusset, number = "
    for bus in Fault_buses:
        if(Fault_buses[0] == bus):
            dbs_str = dbs_str + str(bus)
        else:
            dbs_str = dbs_str + ','+str(bus)
    g.write(dbs_str+')\n')
    
    # write which faults to run 
    for Fault_type in Fault_types:
        if(Fault_type in ['ABC','AG','BC','BCG']):
            for Fault_R in Fault_Res:
                g.write("fault_sim_py('"+str(Fault_R.real)+"',\""+Fault_type+"\",faultbusset,'"+str(Fault_R.imag)+"')\n")
        else:
            print ('Error: Fault type {} not supported'.format(Fault_type))
    
    # Clear fault bus set
    g.write("erset faultbusset\n")
    # save repoer
    g.write("save_report\n")
    
    # clsoe APA
    g.write("screen_reports ON\n")
    if(closeAPA):
        g.write("terminate\n")
    g.close()
    
    return script_abs_path