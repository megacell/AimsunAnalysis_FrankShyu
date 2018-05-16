import sqlite3
import sys
import os
import csv
import math
import datetime
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from os import walk
from utilities import *
from averageCSVFiles import *
from std6_timePathTravelTime import generatePlot as alien

def generatePlot(percentage, timeStep, absNash, outputDir, plotEvent, eventStart, eventEnd):
  #-----------------------------------------------------------#
  # Helper function for generating a plot that compares the   #
  # travel time of App users and non-App users with respect to#
  # the percentage of App users in the network                #
  #-----------------------------------------------------------#
  # For plotting the timestep - abs Nash Distance graph #
  font = {'weight':'bold',
          'size':40}
  plt.rc('font', **font)
  fig, ax = plt.subplots(figsize = (24, 14), dpi = 100)
  for i in range(len(timeStep)):
    timeStep[i] /= 60
  for i in range(len(percentage)):
    ax.plot(timeStep, absNash[i], color = (1 - float(percentage[i])/100, 0, float(percentage[i])/100), \
            label = '{}% App Users'.format(percentage[i]), \
            linewidth = 4.0)
    hand, lab = ax.get_legend_handles_labels()
    plt.legend(handles = hand, loc = 1)
  ax.set_xlabel('Elapsed Time (min)')
  ax.set_ylabel('Path Flow (# of Vehicles)')
  ax.set_title('Path Flow for Different Percentages of App Users')
#  ax.set_ylim([0, 150])
  if plotEvent:
    ymin, ymax = plt.ylim()
    ax.plot([eventStart, eventStart], [ymin, ymax], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
    ax.plot([eventEnd, eventEnd], [ymin, ymax], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
  plt.savefig(outputDir + 'pathFlow.png', dpi = 'figure')



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


def extractSingleDB(fileName, thisPercentage, debug, oriId, desId, maxT, minT):
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
  print(('extracting database:' + fileName))
  vehPathDict = buildVehPathDict(fileName)

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, entranceTime FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND entranceTime > {} AND entranceTime < {} AND origin = {} AND destination = {}'.format(minT, maxT, oriId, desId))
  vehs= cur.fetchall()
  con.close()
  # Key: essentially the timestep (tStep below), this is because we are #
  #      targeting a specific O/D pair.                                 #
  timeStepSize   = 600
  pathTimeSeries = {}
  distinctPaths  = {}
  for veh in vehs:
    thisPath = vehPathDict[veh[0]]
    if hash(tuple(thisPath)) not in distinctPaths:
      distinctPaths[hash(tuple(thisPath))] = thisPath

  for path in list(distinctPaths.keys()):
    dummy = []
    for i in range(int(math.ceil((maxT - minT) / timeStepSize))):
      dummy.append(0)
    pathTimeSeries[path] = dummy

  for veh in vehs:
    thisPath = vehPathDict[veh[0]]
    thisStep = int(math.floor((veh[1] - minT) / timeStepSize))
    pathTimeSeries[hash(tuple(thisPath))][thisStep] += 1

  for key, value in list(pathTimeSeries.items()):
#    if sum(value) > 100:
    print(("hash value is {}, path is ".format(key) + str(distinctPaths[key])))

  return pathTimeSeries

def sortBasedOnPercentage(percentage, pathTimeSeries):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = list(zip(percentage, pathTimeSeries))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sPathTimeSeries = list(map(list, unzip))
  return sPercentage, sPathTimeSeries

def traverseMultiDB(fileList, debug, maxT, minTime):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
  percentage = []
  pathTimeSeries = []
  oriId, desId  = getODPair(fileList[0])
  for filename in fileList:
    thisPercentage  = getPercentage(filename)
    thisPathTimeSeries = extractSingleDB(filename, thisPercentage, debug, oriId, desId, maxT, minTime)
    percentage.append(thisPercentage)
    pathTimeSeries.append(thisPathTimeSeries)
  percentage, pathTimeSeries = sortBasedOnPercentage(percentage, pathTimeSeries)
  return percentage, pathTimeSeries

def printUsage(): 
  print('usage: \n python extractMultiSQLite.py directoryName showAllMessages maxEntranceTime')
  print('directoryName: the directory in which the sqlite databases are stored')
  print('showAllMessages: use "true" to output all messages, recommended')
  print('maxEntranceTime: the maximum time cars are allowed to enter the network')
  print('system exiting...')
  sys.exit()

def std4Call(dirName, maxTime, minTime, plotEvent = False, eventStart = 0, eventEnd = 0):
  print('---------------------------------------')
  print('       executing std4 plots            ')
  print('---------------------------------------')
  fileList = getAllFilenames(dirName)
  percentage, timeStep, absNash, rltNash = traverseMultiDB(fileList, True, maxTime, minTime)
  generatePlot(percentage, timeStep, absNash, rltNash, getOutputDirOld(dirName), plotEvent, eventStart, eventEnd)

def store2CSV(percentage, pathTimeSeries, outputDir):
  outname = outputDir + 'run' + str(runIdx) + '_timePathFlow.csv'
  with open(outname, 'w') as fout:
    for i in range(len(percentage)):
      keyList = list(pathTimeSeries[i].keys())
      for j in range(len(keyList)):
        fout.write(str(percentage[i]))
        fout.write(',' + str(keyList[j]))
        for timeSeriesIdx in range(len(pathTimeSeries[i][keyList[j]])):
          fout.write(',' + str(pathTimeSeries[i][keyList[j]][timeSeriesIdx]))
        if ((i != len(percentage) - 1) or (j != len(keyList) - 1)):
          fout.write('\n')

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  motherDir  = sys.argv[1]
  maxTime  = int(sys.argv[2])
  minTime  = int(sys.argv[3])
  outputDir  = getOutputDir(motherDir, maxTime, minTime, '/timePathFlow/')
  outputDir2  = getOutputDir(motherDir, maxTime, minTime, '/timePathTravelTime/')
  dirList    = [(x[0]+'/') for x in os.walk(motherDir)]
  dirList.remove(motherDir + '/')
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    percentage, pathTimeSeries = traverseMultiDB(fileList, True, maxTime, minTime)
    store2CSV(percentage, pathTimeSeries, outputDir)
  percentage, timeStep, absNash, desiredPath = averageTimePathFlow(outputDir)
  generatePlot(percentage, timeStep, absNash, '../outputFigures/', False, 2*60, 4*60)
  percentage, timeStep, pathFlow = averageTimePathTime(outputDir2, desiredPath)
  alien(percentage, timeStep, pathFlow, '../outputFigures/', False, 2*60, 4*60)
