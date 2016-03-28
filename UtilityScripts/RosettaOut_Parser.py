#Iterates through directories to open Rosetta.out and creates Nested Dictionaries:
#>Prediction ID
#>>Structure ID (nstruct 1-100)
#>>>Structure Type (WT, Mut, DDG)
#>>>>Score Type

import os
import linecache
import json

def parse_rosetta_out(workingdir):
    fattydict = {}
    unfinished = {}
    for i in os.listdir(workingdir):
        if os.path.isdir(workingdir + i):
            print i
            fattydict[i] = {}
            structID = 1
            counter = 0
            filename = workingdir + i + "/rosetta.out"
            for line in enumerate(open(filename, 'r')):
                if line[1].find("fa_atr") == 1:
                    if counter % 2 == 0:
                        linecounter = 0
                        currentline = line[0] + 1
                        fattydict[i]['WT_' + str(structID)] = {}
                        try:
                            while linecache.getline(filename, currentline).strip() != '-----------------------------------------':
                                scores = linecache.getline(filename, currentline)
                                parsed_scores = scores.split()
                                fattydict[i]['WT_' + str(structID)][parsed_scores[0]] = parsed_scores[1]
                                linecounter = linecounter + 1
                                currentline = currentline + 1
                            sumscore = linecache.getline(filename, line[0] + linecounter + 2)
                            parsed_sumscore = sumscore.split()
                            fattydict[i]['WT_' + str(structID)][parsed_sumscore[0]] = parsed_sumscore[2]
                            counter = counter + 1
                        except:
                            print "Oops, something went wrong here..."
                    else:
                        linecounter = 0
                        currentline = line[0] + 1
                        fattydict[i]['Mutant_' + str(structID)] = {}
                        try:
                            while linecache.getline(filename, currentline).strip() != '-----------------------------------------':
                                scores = linecache.getline(filename, currentline)
                                parsed_scores = scores.split()
                                fattydict[i]['Mutant_' + str(structID)][parsed_scores[0]] = parsed_scores[1]
                                linecounter = linecounter + 1
                                currentline = currentline + 1
                            sumscore = linecache.getline(filename, line[0] + linecounter + 2)
                            parsed_sumscore = sumscore.split()
                            fattydict[i]['Mutant_' + str(structID)][parsed_sumscore[0]] = parsed_sumscore[2]
                            counter = counter + 1
                            structID = structID +1
                        except:
                            print "Oops, something went wrong here..."
                else:
                    continue
            print str(i) + ": " + str(structID - 1) + " structures completed"
            
            #Keeps track of unfinished jobs
            if structID - 1 < 100:
                unfinished[i] = structID - 1
            else:
                continue
                
    return fattydict, unfinished

my_working_directory = str(os.getcwd() + '/')
print my_working_directory
parsed_dict, unfinished_jobs = parse_rosetta_out(my_working_directory)

print unfinished_jobs
os.chdir(my_working_directory)

open("DDG_Data.json", "w").write(
    json.dumps(parsed_dict, sort_keys=True,separators=(',', ': ')))