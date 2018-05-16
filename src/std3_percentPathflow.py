import sqlite3
import sys
import os
import csv
import datetime
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from os import walk
from utilities import *
from averageCSVFiles import *
#---------------------------------------------------------------------#
# This python file takes in multiple runs and calculate how the path  #
# flow time of different paths changes with the app user percentage.  # 
# Note that for large networks like the I-210, plotting the path flow #
# of all paths is messy and meaningless because tehre will be too many#
# colors. To get around this problem, you can use another file in this#
# directory: std7_pathflowOneAll, which plots the path flow of the    #
# main path and ALL OTHER paths, instead. Main execution is at the bo-#
# ttom of this file.                                                  #
#---------------------------------------------------------------------#

def generatePlot(percentage, pathFlow, flowStd, unionKeys):
  #-------------------------------------------------------------------#
  # percentage: Sorted list containing all app user percentages       #
  # pathFlow: Average path flow of all paths                          #
  # flowStd: Standard deviation of path flow of all paths             #
  #                                                                   #
  # Note: pathFlow and flowStd are list of dictionaries, as below:    #
  #                                                                   #
  # percentage: [10, ..., 90]                                         #
  # pathFlow: [[path1: 301, path2: 250],..., [path1: 270, path2: 270]]#
  # flowStd: [[path1: 5.5, path2: 2.3],..., [path1: 3.4, path2: 6.6]] #
  #-------------------------------------------------------------------#
  font = {'weight':'bold',
          'size':24}
  plt.rc('font', **font)
  fig, ax1 = plt.subplots(figsize = (24, 14), dpi = 100)
  ax1.set_xlabel('Percentage of App Users (%)')
  ax1.set_ylabel('Path Flow (#)')
  ax1.grid(color = 'b', linestyle = '--', linewidth = 2)

  #-------------------------------------------------------------------#
  # Lookup table for generating different colors for different paths  #
  #-------------------------------------------------------------------#
  colors = getColorChoices(unionKeys)
  keyLookup = mapKey2Int(unionKeys)
  for key in unionKeys:
    localPathFlow = []
    localStd = []
    for i in range(len(percentage)):
      if key in list(pathFlow[i].keys()):
        localPathFlow.append(pathFlow[i][key])
        localStd.append(flowStd[i][key])
      else:
        localPathFlow.append(0)
        localStd.append(0)
#    ax1.plot(percentage, localPathFlow, color = colors[key], label = 'vehicles arrived by taking path {}'.format(keyLookup[key]), linewidth = 5.0)
    ax1.errorbar(percentage, localPathFlow, yerr=localStd, color = colors[key], label = 'Vehicles arrived by taking path {}'.format(keyLookup[key]), linewidth = 5.0, ecolor=colors[key], capsize=5.0, capthick=5.0)

  #-------------------------------------------------------------------#
  # Uncomment next line if you have to fix the upper/lower bounds of  #
  # the y-axis                                                        #
  #-------------------------------------------------------------------#
  #ax1.set_ylim([-100, 6000])
  plt.title('Percentage of App Users - Path Flow')
  hand1, lab1 = ax1.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 0)
  dummy       = plt.gca().add_artist(firstLegend)
  plt.savefig('../outputFigures/percentage-pathflow.png', dpi = 'figure')

def extractSingleDB(fileName, thisPercentage, debug, oriId, desId, maxTime, minTime):
  print('extracting database ' + fileName)
  vehPathDict = buildVehPathDict(fileName)

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND origin = {} AND destination = {} AND entranceTime < {} AND entranceTime > {}'.format(oriId, desId, maxTime, minTime))
  vehFlow = cur.fetchall()
  con.close()

  pathAccumCount= {}
  for veh in vehFlow:
    thisPath = vehPathDict[veh[0]]
    thisPath = list(set(thisPath))
    if hash(tuple(thisPath)) in pathAccumCount:
      pathAccumCount[hash(tuple(thisPath))]+= 1
    else:
      pathAccumCount[hash(tuple(thisPath))] = 1
  
  return pathAccumCount

def sortBasedOnPercentage(percentage, pathFlow):
  #-------------------------------------------------------------------#
  # Helper function to sort all data based on the percentage of app   #
  # users                                                             #
  #-------------------------------------------------------------------#
  zipped = list(zip(percentage, pathFlow))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sPathFlow = list(map(list, unzip))
  return sPercentage, sPathFlow

def traverseMultiDB(fileList, debug, maxTime, minTime):
  #-------------------------------------------------------------------#
  # Traverse multiple SQLite DB and return the average path flow of   #
  # different paths                                                   #
  #-------------------------------------------------------------------#
  percentage = []
  pathFlow   = []
  oriId, desId  = getODPair(fileList[0])
  for filename in fileList:
    thisPercentage  = getPercentage(filename)
    thisPathFlow= \
      extractSingleDB(filename, thisPercentage, debug, oriId, desId, maxTime, minTime)
    percentage.append(thisPercentage)
    pathFlow.append(thisPathFlow)
  percentage, pathFlow = \
    sortBasedOnPercentage(percentage, pathFlow)
  return percentage, pathFlow

def printUsage(): 
  print('usage: \n\t python std3_percentPathFlow.py directoryName maxEntranceTime minEntranceTime')
  print('\t directoryName: the directory in which the sqlite databases are stored')
  print('try \n\t python std3_percentPathFlow.py ../sqliteDatabases/DemoBenchmarkAccident/ 14400 7200')
  sys.exit() 

def store2CSV(percentage, pathFlow, runIdx, outputDir):
  outname = outputDir + 'run' + str(runIdx) + '_pathFlow.csv'
  with open(outname, 'w') as fout:
    for i in range(len(percentage)):
      fout.write(str(percentage[i]))
      for key in list(pathFlow[i].keys()):
        fout.write(',' + str(key) + ',' + str(pathFlow[i][key]))
      if i != (len(percentage) - 1):
        fout.write('\n')

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  #-------------------------------------------------------------------#
  # Parsing input arguments and building list of all directories in   #
  # target (mother) directory                                         #
  #-------------------------------------------------------------------#
  dirList, outputDir, maxTime, minTime = parseArgv(sys.argv, "percentPathFlow")

  #-------------------------------------------------------------------#
  # Traverse, extract, and write data                                 #
  #-------------------------------------------------------------------#
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    percentage, pathFlow = traverseMultiDB(fileList, True, maxTime, minTime)
    store2CSV(percentage, pathFlow, runIdx, outputDir)
  #-------------------------------------------------------------------#
  # Read data from csv file, calculate standard deviation, and plot   #
  #-------------------------------------------------------------------#
  percentage, pathFlow, pathFlowStdDict, unionKeys = averagePathTTime(outputDir + '/')
  generatePlot(percentage, pathFlow, pathFlowStdDict, unionKeys)
