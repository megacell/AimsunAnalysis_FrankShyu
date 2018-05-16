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

#---------------------------------------------------#
# The total demand of the network has to be manually#
# keyed in. This is because there will be cars that #
# fail to enter the network.                        #
#---------------------------------------------------#
totalDemand = 8000

def generatePlot(percentage, pathFlow, std, unionKeys):
  #-----------------------------------------------------------#
  # Helper function for generating a plot that compares the   #
  # travel time of App users and non-App users with respect to#
  # the percentage of App users in the network                #
  #-----------------------------------------------------------#
  font = {'weight':'bold',
          'size':40}
  plt.rc('font', **font)
  fig, ax1 = plt.subplots(figsize = (24, 14), dpi = 100)
  ax1.set_xlabel('Percentage of App Users (%)')
  ax1.set_ylabel('Path Flow (#)')
  ax1.grid(color = 'b', linestyle = '--', linewidth = 2)
  colors = getColorChoices(unionKeys)
  keyLookup = mapKey2Int(unionKeys)
  ylim      = 0
  for key in unionKeys:
    localPathFlow = []
    localPathStd = []
    for i in range(len(percentage)):
      if key in list(pathFlow[i].keys()):
        localPathFlow.append(pathFlow[i][key])
        localPathStd.append(std[i][key])
      else:
        localPathFlow.append(0)
        localPathStd.append(0)
#    ax1.plot(percentage, localPathFlow, color = colors[key], label = 'vehicles arrived by taking path {}'.format(keyLookup[key]), linewidth = 5.0)
    if key == 11111:
      ax1.errorbar(percentage, localPathFlow, yerr=localPathStd, color = colors[key], label = 'Vehicles arrived by taking alternative paths'.format(keyLookup[key]), linewidth = 5.0, ecolor=colors[key], capsize=5.0, capthick=5.0)
    else:
      ax1.errorbar(percentage, localPathFlow, yerr=localPathStd, color = colors[key], label = 'Vehicles arrived by taking the main path'.format(keyLookup[key]), linewidth = 5.0, ecolor=colors[key], capsize=5.0, capthick=5.0)
    if max(localPathFlow) > ylim:
      ylim = max(localPathFlow)
  ax1.set_ylim([0, 1000])
  plt.title('Percentage of App Users - Path Flow')
  hand1, lab1 = ax1.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 1)
  dummy       = plt.gca().add_artist(firstLegend)
  plt.savefig('../outputFigures/percentage-pathflow.png', dpi = 'figure')

def extractSingleDB(fileName, thisPercentage, debug, oriId, desId, maxTime, minTime):
  #----------------------------------------------------------#
  # Helper function to traverse single SQLite DB and return  #
  # the average travel time of different paths               #
  #----------------------------------------------------------#
  # Extracting the interested columns from the database, the #
  # columns of the extracted data are                        #
  # (0) oid, the object id for the generated vehicles        #
  # (1) end, the order of the section traversal for a vehicle#
  # (2) sectionId, the id for the road section               #
  # (3) travelTime, the travel time on the specific section  #
  print('extracting database:')
  print(fileName)
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, ent, sectionId, travelTime FROM MIVEHSECTTRAJECTORY ORDER BY oid ASC, ent ASC')
  rows = cur.fetchall()
  con.close()
  # First we build up the vehicle - path relation for fast lookup   #
  pathList    = []
  lastOid     = rows[0][0]
  vehPathDict = {}
  for i in range(len(rows)):
    thisOid = rows[i][0]
    if i == (len(rows) - 1 ):
      pathList.append(rows[i][2])
      vehPathDict[thisOid] = pathList
    elif lastOid != thisOid:
  # Completed finding the path for 1 single car, record the results  #
      vehPathDict[lastOid] = pathList
      pathList = []
      pathList.append(rows[i][2])
      lastOid  = thisOid
    else:
  # Add a new section to the path of this car                        #
      pathList.append(rows[i][2])

  # Now we select all cars that succeeded in entering and exiting the#
  # network.                                                         #
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND origin = {} AND destination = {} AND entranceTime < {} AND entranceTime > {}'.format(oriId, desId, maxTime, minTime))
  vehTTime = cur.fetchall()
  con.close()
  # Then, for each car, we lookup the travel time and add the result #
  # to the corresponding path                                        #
  pathAccumCount= {}
  for i in range(len(vehTTime)):
    thisPath = vehPathDict[vehTTime[i][0]]
    thisPath = list(set(thisPath))
    if hash(tuple(thisPath)) in pathAccumCount:
      pathAccumCount[hash(tuple(thisPath))]+= 1
    else:
      pathAccumCount[hash(tuple(thisPath))] = 1

  majorPathKey = 0
  majorPathFlow= 0.0
  for key, value in pathAccumCount.items():
    if value > majorPathFlow:
      majorPathFlow = value
      majorPathKey = key
#  I-210, OD 23352 -> 26672 Main Path
#  majorPathKey = -8184786203333384014
#  I-210, OD 23377 -> 23733 Main Path
#  majorPathKey = -1760004654518836601
#  I-210, OD ???
  majorPathKey = -1671812773382780880
  pathAccumCountFilter = {}
  artPathKey = 11111
  pathAccumCountFilter[majorPathKey] = pathAccumCount[majorPathKey]
  pathAccumCountFilter[artPathKey] = 0
  for key, value in pathAccumCount.items():
    if key != majorPathKey:
      pathAccumCountFilter[artPathKey] += value
  print(f"\tpath dictionary is\n{pathAccumCountFilter}")
  return pathAccumCountFilter

def sortBasedOnPercentage(percentage, pathFlow):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = list(zip(percentage, pathFlow))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sPathFlow = list(map(list, unzip))
  return sPercentage, sPathFlow

def traverseMultiDB(fileList, debug, maxTime, minTime):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
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
  print('usage: \n\t python extractMultiSQLite.py directoryName showAllMessages maxTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('system exiting...')
  sys.exit()

def std3Call(dirName, maxTime, minTime):
  print('---------------------------------------')
  print('       executing std3 plots            ')
  print('---------------------------------------')
  fileList = getAllFilenames(dirName)
  percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck = traverseMultiDB(fileList, True, maxTime, minTime)
  generatePlot(percentage, pathAvgTime, pathFlow, commonKeys, countNonEnter, countStuck, getOutputDir(dirName))

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
  motherDir  = sys.argv[1]
  maxTime  = int(sys.argv[2])
  minTime  = int(sys.argv[3])
  outputDir  = getOutputDir(motherDir, maxTime, minTime, '/pathflow/')
  dirList    = [(x[0]+'/') for x in os.walk(motherDir)]
  dirList.remove(motherDir + '/')
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    percentage, pathFlow = traverseMultiDB(fileList, True, maxTime, minTime)
    store2CSV(percentage, pathFlow, runIdx, outputDir)
  percentage, pathFlow, std, unionKeys = averagePathTTime(outputDir + '/')
  print(f"pathflow is {pathFlow}")
  generatePlot(percentage, pathFlow, std, unionKeys)
