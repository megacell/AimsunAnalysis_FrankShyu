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
totalDemand = 32000
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
  ax1.set_ylabel('Path Travel Time (sec)')
  ax1.grid(color = 'b', linestyle = '--', linewidth = 2)
  colors = getColorChoices(unionKeys)
  keyLookup = mapKey2Int(unionKeys)
  ylim = 0
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
#    ax1.plot(percentage, localPathFlow, color = colors[key], label = 'average travel time of path {}'.format(keyLookup[key]), linewidth = 5.0)
    if key == 1111:
      ax1.errorbar(percentage, localPathFlow, yerr=localPathStd, color = colors[key], label = 'Average travel time of alternative paths'.format(keyLookup[key]), linewidth = 5.0, ecolor=colors[key], capsize=5.0, capthick=5.0)
    else:
      ax1.errorbar(percentage, localPathFlow, yerr=localPathStd, color = colors[key], label = 'Average travel time of the main path'.format(keyLookup[key]), linewidth = 5.0, ecolor=colors[key], capsize=5.0, capthick=5.0)
    if max(localPathFlow) > ylim:
      ylim = max(localPathFlow)
  ax1.set_ylim([1200, 1700])
  plt.title('Percentage of App Users - Path Travel Time')
  hand1, lab1 = ax1.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 1)
  dummy       = plt.gca().add_artist(firstLegend)
  plt.savefig('../outputFigures/percentage-pathTTime.png', dpi = 'figure')

def buildVehPathDict(fileName):
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, ent, sectionId, travelTime FROM MIVEHSECTTRAJECTORY ORDER BY oid ASC, ent ASC')
  rows = cur.fetchall()
  con.close()
  pathList    = []
  lastOid     = rows[0][0]
  vehPathDict = {}
  for i in range(len(rows)):
    thisOid = rows[i][0]
    if i == (len(rows) - 1 ):
      pathList.append(rows[i][2])
      vehPathDict[thisOid] = pathList
    elif lastOid != thisOid:
      vehPathDict[lastOid] = pathList
      pathList = []
      pathList.append(rows[i][2])
      lastOid  = thisOid
    else:
      pathList.append(rows[i][2])
  return vehPathDict

def getVehStuck(fileName, minTime, maxTime):
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT COUNT(oid) FROM MIVEHTRAJECTORY WHERE exitTime = -1 AND entranceTime > {} AND entranceTime < {}'.format(minTime, maxTime))
  vehStuck = cur.fetchall()
  con.close()
  countStuck = vehStuck[0][0]
  return countStuck

def getSimLength(fileName):
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT MAX(entranceTime) FROM MIVEHTRAJECTORY WHERE entranceTime > 0')
  simLength = cur.fetchall()
  con.close()
  simLength = simLength[0][0]
  return simLength

def extractSingleDB(fileName, thisPercentage, debug, oriId, desId, maxTime, minTime):
  print(('extracting database:' + fileName))
  vehPathDict = buildVehPathDict(fileName)

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND origin = {} AND destination = {} AND entranceTime < {} AND entranceTime > {}'.format(oriId, desId, maxTime, minTime))
  vehTTime = cur.fetchall()
  vehEnter = len(vehTTime)
  con.close()
  pathAccumTime = {}
  pathAccumCount= {}
  for i in range(len(vehTTime)):
    thisPath = vehPathDict[vehTTime[i][0]]
    thisPath = list(set(thisPath))
    if hash(tuple(thisPath)) in pathAccumTime:
      pathAccumTime[hash(tuple(thisPath))] += vehTTime[i][1]
      pathAccumCount[hash(tuple(thisPath))]+= 1
    else:
      pathAccumTime[hash(tuple(thisPath))]  = vehTTime[i][1]
      pathAccumCount[hash(tuple(thisPath))] = 1
  
  majorPathKey = 0
  majorPathFlow= 0.0
  for key, value in pathAccumCount.items():
    if value > majorPathFlow:
      majorPathFlow = value
      majorPathKey = key
#  majorPathKey = -8184786203333384014
#  majorPathKey = -1760004654518836601
  majorPathKey = -1671812773382780880

  pathCountFilter = {}
  pathTimeFilter  = {}
  artPathKey = 1111
  pathCountFilter[majorPathKey] = pathAccumCount[majorPathKey]
  pathCountFilter[artPathKey] = 0
  pathTimeFilter[majorPathKey] = pathAccumTime[majorPathKey]
  pathTimeFilter[artPathKey] = 0

  for key in pathAccumCount.keys():
    if key != majorPathKey:
      pathCountFilter[artPathKey] += pathAccumCount[key] 
      pathTimeFilter[artPathKey] += pathAccumTime[key] 

  pathAvgTime = {}
  for key in pathCountFilter.keys():
#    if value > 0.05 * len(vehTTime):
    pathAvgTime[key] = pathTimeFilter[key]/pathCountFilter[key]

  countStuck = getVehStuck(fileName, minTime, maxTime)
  simLength = getSimLength(fileName)
  countNonEnter = (totalDemand * (maxTime - minTime) / simLength) - (vehEnter + countStuck)
  return pathAvgTime

def sortBasedOnPercentage(percentage, pathAvgTime):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = list(zip(percentage, pathAvgTime))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sPathAvgTime = list(map(list, unzip))
  return sPercentage, sPathAvgTime

def traverseMultiDB(fileList, debug, maxTime, minTime):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
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
  print('usage: \n\t python extractMultiSQLite.py directoryName showAllMessages maxTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('system exiting...')
  sys.exit()

def store2CSV(percentage, pathFlow, runIdx, outputDir):
  outname = outputDir + 'run' + str(runIdx) + '_pathTTime.csv'
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
  outputDir  = getOutputDir(motherDir, maxTime, minTime, '/pathttime/')
  dirList    = [(x[0]+'/') for x in os.walk(motherDir)]
  dirList.remove(motherDir + '/')
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    percentage, pathAvgTime = traverseMultiDB(fileList, True, maxTime, minTime)
    store2CSV(percentage, pathAvgTime, runIdx, outputDir)
  Percentage, PercentFlowDict, std, unionKeys = averagePathTTime(outputDir + '/')
  generatePlot(Percentage, PercentFlowDict, std, unionKeys)
