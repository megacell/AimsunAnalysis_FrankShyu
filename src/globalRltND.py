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

def generatePlot(percentage, timeStep, absNash, outputDir, plotEvent, eventStart, eventEnd):
  #-----------------------------------------------------------#
  # Helper function for generating a plot that compares the   #
  # travel time of App users and non-App users with respect to#
  # the percentage of App users in the network                #
  #-----------------------------------------------------------#
  # For plotting the timestep - abs Nash Distance graph #
  font = {'weight':'bold',
          'size':20}
  plt.rc('font', **font)
  fig, ax = plt.subplots(figsize = (24, 14), dpi = 100)
  for i in xrange(len(percentage)):
    ax.plot(timeStep, absNash[i], color = (1 - float(percentage[i])/100, 0, float(percentage[i])/100), \
            label = 'Rlt Nash Distance of percentage {}'.format(percentage[i]), \
            linewidth = 4.0)
    hand, lab = ax.get_legend_handles_labels()
    plt.legend(handles = hand, loc = 1)
  ax.set_xlabel('Elapsed Time (sec)')
  ax.set_ylabel('Relative Nash Distance (%)')
  ax.set_title('Relative Nash Distance for Different App User Percentages')
  ax.set_ylim([0, 3 * max(max(absNash))])
  if plotEvent:
    ymin, ymax = plt.ylim()
    ax.plot([eventStart, eventStart], [ymin, ymax], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
    ax.plot([eventEnd, eventEnd], [ymin, ymax], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
  plt.savefig(outputDir + 'rltND.png', dpi = 'figure')


#------------------------------------------------------------#
# Global variables to plot additional lines to describe when #
# an event (i.e., an accident) starts.                       #
#------------------------------------------------------------#

def removeSubsetPaths(pathAccumTime, pathAccumCount):
  #----------------------------------------------------------#
  # Helper function to remove paths that are subsets of other#
  # paths. For example, if a path contains sections (1, 2, 3)#
  # and there is another path that contains sections (1, 2), #
  # the latter one will be removed                           #
  # ---------------------------------------------------------#
  newPathAccumTime = {} 
  newPathAccumCount= {}
  for key in pathAccumTime.keys():
    isSubset = False
    for compKey in pathAccumTime.keys():
      if (key.issubset(compKey) and key != compKey ):
        isSubset = True
    if (not isSubset):
      newPathAccumTime[key] = pathAccumTime[key]
      newPathAccumCount[key]= pathAccumCount[key]
  return newPathAccumTime, newPathAccumCount

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
  print('extracting database:' + fileName)

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, entranceTime, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND entranceTime > {} AND entranceTime < {} AND origin = {} AND destination = {}'.format(minT, maxT, oriId, desId))
  vehTTime = cur.fetchall()
  con.close()
  # Key: essentially the timestep (tStep below), this is because we are #
  #      targeting a specific O/D pair.                                 #
  tStepAccumTime = {}
  tStepAccumCount= {}
  tStepMinTime   = {}
  timeStepSize   = 600
  for i in xrange(len(vehTTime)):
    thisTStep = math.floor((vehTTime[i][1] - minT)/timeStepSize)
    if thisTStep in tStepAccumTime:
      tStepAccumTime[thisTStep] += vehTTime[i][2]
      tStepAccumCount[thisTStep]+= 1
      if vehTTime[i][2] < tStepMinTime[thisTStep]:
        tStepMinTime[thisTStep] = vehTTime[i][2]
    else:
      tStepAccumTime[thisTStep]  = vehTTime[i][2]
      tStepAccumCount[thisTStep] = 1
      tStepMinTime[thisTStep]    = vehTTime[i][2]
  tStep   = []
  absNash = []
  rltNash = []
  count   = 0
  for i in xrange(int(math.ceil((maxT - minT) / timeStepSize))):
    tStep.append(i * timeStepSize)
    if i in tStepMinTime:
      absNash.append(tStepAccumTime[i]/tStepAccumCount[i] - tStepMinTime[i])
      rltNash.append(100 * absNash[i] / (tStepAccumTime[i] / tStepAccumCount[i]))
    else:
      absNash.append(0)
      rltNash.append(0)
      count += 1
  return tStep, absNash, rltNash

def sortBasedOnPercentage(percentage, absNash, rltNash):
  #----------------------------------------------------------#
  # Helper function to sort all data based on the percentage #
  # of App users                                             #
  #----------------------------------------------------------#
  zipped = zip(percentage, absNash, rltNash)
  zipped.sort()
  unzip  = zip(*zipped)
  sPercentage, sAbsNash, sRltNash = map(list, unzip)
  return sPercentage, sAbsNash, sRltNash

def traverseMultiDB(fileList, debug, maxT, minTime):
  #----------------------------------------------------------#
  # Traverses multiple DB and return the average travel time #
  # (i.e. TTime) of app users and non-app users              #
  #----------------------------------------------------------#
  percentage = []
  absNash    = []
  rltNash    = []
  tStep      = []
  oriId, desId  = getODPair(fileList[0])
  for filename in fileList:
    thisPercentage  = getPercentage(filename)
    thisTStep, thisAbsNash, thisRltNash = extractSingleDB(filename, thisPercentage, debug, oriId, desId, maxT, minTime)
    percentage.append(thisPercentage)
    absNash.append(thisAbsNash)
    rltNash.append(thisRltNash)
    tStep = thisTStep
  percentage, absNash, rltNash = sortBasedOnPercentage(percentage, absNash, rltNash)
  return percentage, tStep, absNash, rltNash

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

def store2CSV(percentage, absND, runIdx, outputDir):
  outname = outputDir + 'run' + str(runIdx) + '_timeRltND.csv'
  with open(outname, 'wb') as fout:
    for i in xrange(len(percentage)):
      fout.write(str(percentage[i]))
      for j in xrange(len(absND[i])):
        fout.write(',' + str(absND[i][j]))
      if i != (len(percentage) - 1):
        fout.write('\n')

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  motherDir  = sys.argv[1]
  maxTime  = int(sys.argv[2])
  minTime  = int(sys.argv[3])
  outputDir  = getOutputDir(motherDir, maxTime, minTime, '/timeRltND/')
  dirList    = [(x[0]+'/') for x in os.walk(motherDir)]
  dirList.remove(motherDir + '/')
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    percentage, timeStep, absNash, rltNash = traverseMultiDB(fileList, True, maxTime, minTime)
    store2CSV(percentage, rltNash, runIdx, outputDir)
  percentage, timeStep, rltNash = averageTimeND(outputDir)
  generatePlot(percentage, timeStep, rltNash, '../outputFigures/', False, 2*3600, 4*3600)
