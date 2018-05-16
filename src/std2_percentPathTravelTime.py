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
# travel time of different paths changes with the app user percentage.# 
# Note that for large networks like the I-210, plotting the travel    #
# time of all paths is messy and meaningless because tehre will be too#
# many colors. To get around this problem, you can use another file in#
# this directory: std8_pathtimeOneAll, which plots the travel time of #
# the main path and ALL OTHER paths, instead. Main execution  is at   #
# the bottom of this file.                                            #
#---------------------------------------------------------------------#

def generatePlot(percentage, pathTime, timeStd, unionKeys):
  #-------------------------------------------------------------------#
  # percentage: Sorted list containing all app user percentages       #
  # pathTime: Average travel time of all paths                        #
  # timeStd: Standard deviation of travel time of all paths           #
  #                                                                   #
  # Note: pathTime and timeStd are list of dictionaries, as below:    #
  #                                                                   #
  # percentage: [10, ..., 90]                                         #
  # pathTime: [[path1: 301, path2: 250],..., [path1: 270, path2: 270]]#
  # timeStd: [[path1: 5.5, path2: 2.3],..., [path1: 3.4, path2: 6.6]] #
  #-------------------------------------------------------------------#
  font = {'weight':'bold',
          'size':24}
  plt.rc('font', **font)
  fig, ax1 = plt.subplots(figsize = (24, 14), dpi = 100)

  ax1.set_xlabel('Percentage of App Users (%)')
  ax1.set_ylabel('Path Travel Time (sec)')
  ax1.grid(color = 'b', linestyle = '--', linewidth = 2)

  #-------------------------------------------------------------------#
  # Lookup table for generating different colors for different paths  #
  #-------------------------------------------------------------------#
  colors = getColorChoices(unionKeys)
  keyLookup = mapKey2Int(unionKeys)

  for key in unionKeys:
    localPathTime = []
    localPathStd = []
    for i in range(len(percentage)):
      if key in list(pathTime[i].keys()):
        localPathTime.append(pathTime[i][key])
        localPathStd.append(timeStd[i][key])
      else:
        localPathTime.append(0)
        localPathStd.append(0)
    ax1.errorbar(percentage, localPathTime, yerr=localPathStd, color = colors[key], label = 'Average travel time of path {}'.format(keyLookup[key]), linewidth = 5.0, ecolor=colors[key], capsize=5.0, capthick=5.0)
  #-------------------------------------------------------------------#
  # Uncomment next line if you have to fix the upper/lower bounds of  #
  # the y-axis                                                        #
  #-------------------------------------------------------------------#
  #ax1.set_ylim([305, 345])

  plt.title('Percentage of App Users - Path Travel Time')
  hand1, lab1 = ax1.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 1)
  dummy       = plt.gca().add_artist(firstLegend)
  plt.savefig('../outputFigures/percentage-pathTTime.png', dpi = 'figure')


def extractSingleDB(fileName, thisPercentage, debug, oriId, desId, maxTime, minTime):
  print(('extracting database ' + fileName))
  vehPathDict = buildVehPathDict(fileName)

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND origin = {} AND destination = {} AND entranceTime < {} AND entranceTime > {}'.format(oriId, desId, maxTime, minTime))
  vehTTime = cur.fetchall()
  con.close()
  pathAccumTime = {}
  pathAccumCount= {}
  for veh in vehTTime:
    thisPath = vehPathDict[veh[0]]
    thisPath = list(set(thisPath))
    if hash(tuple(thisPath)) in pathAccumTime:
      pathAccumTime[hash(tuple(thisPath))] += veh[1]
      pathAccumCount[hash(tuple(thisPath))]+= 1
    else:
      pathAccumTime[hash(tuple(thisPath))]  = veh[1]
      pathAccumCount[hash(tuple(thisPath))] = 1
  
  pathAvgTime = {}
  for key, value in list(pathAccumCount.items()):
    pathAvgTime[key] = pathAccumTime[key]/pathAccumCount[key]

  return pathAvgTime

def sortBasedOnPercentage(percentage, pathAvgTime):
  #-------------------------------------------------------------------#
  # Helper function to sort all data based on the percentage of app   #
  # users                                                             #
  #-------------------------------------------------------------------#
  zipped = list(zip(percentage, pathAvgTime))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sPathAvgTime = list(map(list, unzip))
  return sPercentage, sPathAvgTime

def traverseMultiDB(fileList, debug, maxTime, minTime):
  #-------------------------------------------------------------------#
  # Traverse multiple SQLite DB and return the average travel time of #
  # different paths                                                   #
  #-------------------------------------------------------------------#
  percentage = []
  pathAvgTime= []
  oriId, desId  = getODPair(fileList[0])
  for filename in fileList:
    thisPercentage  = getPercentage(filename)
    thisPathAvgTime = \
      extractSingleDB(filename, thisPercentage, debug, oriId, desId, maxTime, minTime)
    percentage.append(thisPercentage)
    pathAvgTime.append(thisPathAvgTime)
  percentage, pathAvgTime = \
    sortBasedOnPercentage(percentage, pathAvgTime)
  return percentage, pathAvgTime

def printUsage(): 
  print('usage: \n\t python std2_percentPathTravelTime.py directoryName maxEntranceTime minEntranceTime')
  print('\t directoryName: the directory in which the sqlite databases are stored')
  print('try \n\t python std2_percentPathTravelTime.py ../sqliteDatabases/DemoBenchmarkAccident/ 14400 7200')
  sys.exit() 

def store2CSV(percentage, pathTime, runIdx, outputDir):
  outname = outputDir + 'run' + str(runIdx) + '_pathTTime.csv'
  with open(outname, 'w') as fout:
    for i in range(len(percentage)):
      fout.write(str(percentage[i]))
      for key in list(pathTime[i].keys()):
        fout.write(',' + str(key) + ',' + str(pathTime[i][key]))
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
  dirList, outputDir, maxTime, minTime = parseArgv(sys.argv, "percentTravelTime")

  #-------------------------------------------------------------------#
  # Traverse, extract, and write data                                 #
  #-------------------------------------------------------------------#
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    percentage, pathAvgTime = traverseMultiDB(fileList, True, maxTime, minTime)
    store2CSV(percentage, pathAvgTime, runIdx, outputDir)
  #-------------------------------------------------------------------#
  # Read data from csv file, calculate standard deviation, and plot   #
  #-------------------------------------------------------------------#
  Percentage, PercentTimeDict, PercentTimeStdDict, unionKeys = averagePathTTime(outputDir + '/')
  generatePlot(Percentage, PercentTimeDict, PercentTimeStdDict, unionKeys)
