# -*- coding: utf-8 -*-
"""
load APA functions
"""

if __package__ in [None, '']:
    # Database 
    from APA_DB_Functions import connect_to_DB
    from APA_DB_Functions import get_fdb_cursor
    from APA_DB_Functions import get_TableNames
    from APA_DB_Functions import get_Table_Data
    from APA_DB_Functions import get_Tables

    # Network Infor 
    from APA_DB_Functions import get_lines_info
    from APA_DB_Functions import get_Buses_info
    from APA_DB_Functions import get_Loads_info
    from APA_DB_Functions import get_switches_info
    from APA_DB_Functions import get_transformers_info
    from APA_DB_Functions import get_machine_data
    
    # Network mods
    from APA_DB_Functions import add_Bus_to_DB
    from APA_DB_Functions import set_machine_type
    from APA_DB_Functions import add_line_to_DB
    from APA_DB_Functions import add_load_to_DB
    
    # scripts
    from APA_DB_Functions import run_CUPL_script
    from APA_SC_Functions import write_short_circuit_script
    
    # utils
    from APA_DB_Functions import check_sql_str
else:
    from .APA_DB_Functions import connect_to_DB
    from .APA_DB_Functions import get_fdb_cursor
    from .APA_DB_Functions import get_TableNames
    from .APA_DB_Functions import get_Table_Data
    from .APA_DB_Functions import get_Tables

    # Network Infor 
    from .APA_DB_Functions import get_lines_info
    from .APA_DB_Functions import get_Buses_info
    from .APA_DB_Functions import get_Loads_info
    from .APA_DB_Functions import get_switches_info
    from .APA_DB_Functions import get_transformers_info
    from .APA_DB_Functions import get_machine_data
    
    # Network mods
    from .APA_DB_Functions import add_Bus_to_DB
    from .APA_DB_Functions import set_machine_type
    from .APA_DB_Functions import add_line_to_DB
    from .APA_DB_Functions import add_load_to_DB
    
    # scripts
    from .APA_DB_Functions import run_CUPL_script
    from .APA_SC_Functions import write_short_circuit_script
    
    # Utils
    from .APA_DB_Functions import check_sql_str
    
