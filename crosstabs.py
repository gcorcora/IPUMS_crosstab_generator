#!/usr/bin/env python3

#Generating crosstabs
#a lot of functions stolen from universe_ML_checker

#Future Directions:

#could .pipe() make this better?
#could build up to implement classes in conjunction with other classes implementing for ML checker
#split up data loading and label mapping into two functions- better practice

#add logging for issues, not print statements

#repeated strip not needed, can remove

"""
crosstabs_test.py

Written by Gretchen Corcoran, August 2025

Takes in a sample and a list of variables, runs crosstabs, and outputs results with labels to excel, formatted for input into translation table excel file.

Usage:
    python3 crosstabs.py sample_name variable variable

    Example:
        python3 crosstabs.py bd2018ir v101 v501
"""

import pandas as pd
import itertools
import re
import os
import csv
import sys
import argparse
from typing import Tuple, List, Dict
import numpy as np


#General procedure:

#take in user-defined variable names and sample

#read fixed width metadata - load ONLY those user-defined vars

#generate crosstabs with labels

#output to excel


def find_name_and_year(sample_name: str) -> list[str]:
    """
    ***DHS SPECIFIC FOR NOW***
    Decomposes sample name into separate country name, year, and unit of analysis. Pulls country name and path from dhs countries metadata file

    *Future directions: Don't hardcode metadata path to country file
    """
    #could turn into dict if plan to use multiple times
    #traverse to metadata and find countries
    ###########DHS SPECIFIC##############
    country_file = 'countries.xlsx' ##changed to mask full path
    sample_code = sample_name[0:2] #grab first two letters
    year = sample_name[2:6] #grab year
    unit_of_analysis = sample_name[6:8] #grabbing last two for unit of analysis (ir, br, kr)
    try:
        country_df = pd.read_excel(country_file)
    except Exception as e:
        print(f'Failed to load {country_file}: {e}')

    country_name_row = country_df[country_df['country']==sample_code]
    if not country_name_row.empty:
        country_name = country_name_row['fullname'].values[0]
        country_folder_path = country_name_row['path'].values[0]
    else:
        raise ValueError(f'No country found for given sample: {sample_name}')
    #if spaces in country name, need to replace with underscore
    country_name = country_name.lower().replace(" ", "_")
    return [country_name, year, unit_of_analysis, country_folder_path]

def load_data_dict(excel_path: str, user_vars: List[str]) -> Tuple[
    List[Tuple[int, int]],
    List[Tuple[str, str]],
    Dict[str, Dict[str, str]],
    List[Tuple[str, str]]]:
    """"
    Loads relevant columns and variable metadata from a sample's excel-based data dictionary.
    Returns a list of column and width for specified variables (colspecs - List[Tuple[int, int]]), 
    variable names and labels (e.g., V012 - "Age") (var_name_labels - List[Tuple[str,str]]), 
    a dictionary of values and value labels for each variable (if applicable) (value_labels_dict - Dict[str, Dict[str,str]]),
    and a list of variables and their associated svars (svars - List[Tuple[str,str]]).

    Helps ingesting .dat file
    
    Inputs:
        Path to excel file data dictionary
        Specified list of variables to use
    """
    #First list is col specs - start-end of each var
    #Second list is match of variable names + varlabel
    #third is Dict with mapping from variable name to list of value, label pairs
    #this is a bit unwieldy, may simplify later
    if not excel_path.endswith(".xlsx"):
        raise ValueError(f'File {excel_path} is not an .xlsx file.')
    
    #only load specific columns to speed up time
    cols_to_use = ["Var", "Col", "Wid", "Value", "ValueLabel", "VarLabel", "Svar"]
    data_dict_df = pd.read_excel(excel_path, usecols=cols_to_use, engine = "openpyxl")

    colspecs = []
    var_name_labels = []
    svars = []
    value_labels_dict: Dict[str, Dict[str, str]] = {}    

    current_var: str = None
    keep_var = False

    for _, row in data_dict_df.iterrows():
        var_cell = row.get("Var")
        value = row.get("Value")
        label = row.get("ValueLabel")

        try:
            if pd.notna(var_cell): #if is the start of a variable
                var_code = str(var_cell).strip()
                keep_var = var_code in user_vars #boolean
                if not keep_var:
                    #don't need var in df if not going to be in crosstab
                    current_var = None
                    continue

                var_label = str(row.get("VarLabel", "")).strip()
                var_name_labels.append((var_code, var_label)) #e.g., [v101, "Province"] 

                start = int(row["Col"]) -1 #-1 for proper indexing
                width = int(row["Wid"])
                colspecs.append((start, start+width))

                svar = str(row.get("Svar", "")).strip()
                svars.append((var_code, svar))

                current_var = var_code #need to save for value_label_pairs dict
                if current_var not in value_labels_dict:
                    value_labels_dict[current_var] = {}


            elif keep_var and current_var and pd.notna(value): #If there is a value label pair here
                value_str = str(value).strip()
                label_str = str(label).strip() if pd.notna(label) else "" #[no label] if doesn't exist or "" - I think "" is better
                value_labels_dict[current_var][value_str] = label_str
                #gives output like value_labels["v025"]["1"] = "Urban"

        except Exception as e:
            print(f'Error with row processing in data dictionary: {e}')

    return colspecs, var_name_labels, value_labels_dict, svars


def load_microdata(dat_path: str, colspecs: list[tuple[int, int]], var_name_labels: list[tuple[str, str]], value_labels_dict: Dict[str, Dict[str,str]], svars: list[str, str]) -> pd.DataFrame:
    """
    Loads a .dat microdata file and parses it based on specified inputs. Returns a pandas data frame.

    Inputs: 
        dat_path - path to .dat file
        colspecs - list of tuples containing start and width for each variable
        var_name_labels - list of tuples containing variable codes (e.g., v012) and their labels (e.g., "age)
        value_labels_dict - a nested dictionary with variable names as keys, attaching the values and their labels

    Outputs:
        pandas df

    Notes: If value is not in value_labels_dict (like if say, alpha variable, or some sort of hidden variable in data dictionary), will just return number itself as label in df
    """
    var_names = [var for var, label in var_name_labels]
    var_names_labels_dict = dict(var_name_labels)
    df = pd.read_fwf(dat_path, colspecs = colspecs, names = var_names, dtype=str) 
    df.attrs["var_labels"] = var_names_labels_dict #call later with df.attrs["var_labels"]["v101"] to get

    svars_dict = dict(svars)
    df.attrs["svars"] = svars_dict

    #adding in value labels
    for var in var_names:
        if var in value_labels_dict:
            df[var] = df[var].astype(str).str.strip() #need to do for .map() string keys
            label_col = f'{var}_label'
            code_label_col = f'{var}_code_and_label'

            df[label_col] = df[var].map(value_labels_dict[var]) #returns label if in nested dict in value_labels_dict

            #if label was not found in dict, fill in with original number
            df[label_col] = df[label_col].fillna(df[var])

            #use vectorized form
            df[label_col] = clean_label_columns(df, label_col)

            df[code_label_col] = np.where(df[label_col] != df[var], df[var] + ": " + df[label_col], df[var])
            # df[code_label_col] = df[var] + ": " + df[label_col]
            # df[code_label_col] = df[code_label_col].where(df[label_col] != "", df[var])

    return df

def clean_label_columns(df: pd.DataFrame, label_col:str) -> pd.Series:
    """
    Written by chatgpt to help speed up processing
    Cleans value labels, turns into a pandas series
    """
    return df[label_col].fillna("").astype(str).str.strip()

#including functionality so user can specify output excel path
def generate_crosstab_combo(sample_name: str, df: pd.DataFrame, user_vars: List[str], output_excel_path: str) -> str:
    """
    Generates crosstabs and outputs formatting in excel for input into translation tables

    Inputs: 
        sample_name
        pandas data frame
        list of specified variables
        Path to location of output excel file

    Outputs:

        str location of excel output file
    """
    for var in user_vars:
        if var not in df.columns:
            raise ValueError(f'Data dictionary missing expected variable column: {var}')

        label_col = f'{var}_label'
        if label_col not in df.columns:
            df[label_col] = "" #empty if no label?

    
    #concatenation of raw codes
    #vectorized form
    df["code"] = df[user_vars].astype(str).agg(lambda x: "".join(x.str.strip()), axis = 1)

    #concatenate
    label_cols = [f"{var}_code_and_label" for var in user_vars]
    df["label_string"] = df[label_cols].agg(
        lambda row: "; ".join(val if pd.notna(val) and str(val).strip() != "" else ""
                              for val in row), axis = 1)


    combo_df = df.groupby(["code", "label_string"]).size().reset_index(name="Frequency")
    #vectorized formatting version
    combo_df["codes_and_freqs"] = (
        combo_df["code"]
        .str.cat(combo_df["label_string"], sep=" = ")
        .str.cat(combo_df["Frequency"].astype(str).radd(" {").add("}"))
    )

    final_df = combo_df[["codes_and_freqs"]]

    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        #First line, sample name
        pd.DataFrame([[sample_name]]).to_excel(writer, index=False, header=False, startrow = 0)
        #Second line, "P"
        pd.DataFrame([['P']]).to_excel(writer, index=False, header=False, startrow=1)
        #3 lines of blank

        #SVARS GO HERE
        svars_dict = df.attrs.get("svars", {})
        svars = [svars_dict.get(var, " ") for var in user_vars] #is this really necessary? earlier we filtered, but perhaps is good to sanitize
        pd.DataFrame([[" ".join(svars)]]).to_excel(writer, index=False, header=False, startrow=5)
        
        #2 lines of blank

        #Concatenated variables codes
        pd.DataFrame([[" ".join(user_vars)]]).to_excel(writer, index=False, header=False, startrow=8)
        
        #variable labels go here
        var_labels_dict = df.attrs.get("var_labels", {})
        var_labels = [var_labels_dict.get(var, " ") for var in user_vars]
        pd.DataFrame([[";".join(var_labels)]]).to_excel(writer, index=False, header=False, startrow=9)

        #2 lines of blank

        #concatenated codes + freqs
        final_df.to_excel(writer, index = False, header=False, startrow=12)

    return output_excel_path

def main():
    parser = argparse.ArgumentParser(
        description = "Generate crosstabs on specified variables"
    )
    parser.add_argument("sample_name", help = "Name of the DHS sample (e.g., bd2018ir)")
    parser.add_argument("variable_names", nargs = "+", help = "List of variable names to include in crosstab")

    args = parser.parse_args()

    sample_name = args.sample_name.lower()
    variable_names = args.variable_names
    variable_names =[var.lower() for var in args.variable_names]

    try:
        ##find the data dictionary and the .dat file
        #step one, grab the meaning of the the two letter code
        sample_info = find_name_and_year(sample_name) #list with country_name, year, unit of analysis
    except Exception as e:
        print(f'find_name_and_year from sample failed. Did you type the sample abbreviation correctly? {sample_name}')
        print(f'More error text: {e}')
        sys.exit(1)

    #now that we have the sample info, we can grab the data dictionary and .dat files!
    #sample_info[3] is part of excel path from countries cf

    #future direction: change to read in samples CF too to just grab direct path to data dict and dat
    data_dict_excel_path = f'/{sample_info[3]}/{sample_info[1]}/data/data_dict_{sample_name}.xlsx' ##changed to mask full path
    dat_path = f'/{sample_info[3]}/{sample_info[1]}/data/{sample_name}.dat' ##changed to mask full path

    #loading excel data dict
    try:
        colspecs, var_name_labels, values_dict_lookups, svars = load_data_dict(data_dict_excel_path, variable_names)
    except Exception as e:
        print(f'Failed to load {data_dict_excel_path}; {e}')
        #if failed to load files
        sys.exit(1)
    
    #loading fixed_width data
    try:
        df = load_microdata(dat_path, colspecs, var_name_labels, values_dict_lookups, svars)

    except Exception as e:
        print(f'Failed to load .dat file {dat_path}; {e}')
        sys.exit(1)

    #if that all worked, then generate a crosstab
    try:
        #generate crosstab
        output_dir = os.getcwd()
        output_path = os.path.join(output_dir, f'{sample_name}_crosstab.xlsx')

        excel_output_path = generate_crosstab_combo(sample_name, df, variable_names, output_path)
        print(f'Output written to: {excel_output_path}')

    except Exception as e:
        print(f'Failed to generate crosstab; {e}')
        sys.exit(1)

    #is there a way to utilize .pipe() to make this easier/more efficeint?

if __name__ == "__main__":
    main()
