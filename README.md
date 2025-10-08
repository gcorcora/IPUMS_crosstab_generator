Created for IPUMS-DHS - with plans to expand for IPUMS-MICS when researchers are ready to collaborate on desired functionality.

Generates crosstabs from .dat sample data and researcher's .xlsx data dictionaries. Takes in a sample name and a list of variables (allowing multiple variables). Results outputted with labels.

Output is in excel to align with researcher's preferred methods of dealing with variable data. Output formatted to easily copy+paste into relevant files.

Future expansions:
  adding functionality for IPUMS-MICS project - requires changes to folder traversal methods for efficiency
  Some efficiency could be achieved via classes from internal ipums metadata modules - however not sufficient, due to lack of classes handling .dat files. Could create this myself.
  Researcher requested different naming convention for output excel file and ability to specify output location
  Not currently wanted by researchers but could add functionality to handle multiple samples
