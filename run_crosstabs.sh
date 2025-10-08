#!/bin/bash

#Created by Gretchen Corcoran - chatgpt helped with faster conda spin up.
#If issue, check conda activation

CONDA="/pkg/ipums/programming/conda/v4.8/bin/conda"
ENV_NAME="universe_checker"

eval "$($CONDA shell.bash hook)"
conda activate $ENV_NAME

if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
    echo ""
    echo "Usage for DHS: run_crosstabs.sh sample_name var1 [var2 ...]"
    echo "Example:"
    echo "run_crosstabs.sh bd2018ir v025 v101 v501"
    echo ""
    exit 1
fi

python /pkg/ipums/dhs/staff/gretchen_corcoran/python_scripts/crosstabs.py "$@"