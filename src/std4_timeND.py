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
#---------------------------------------------------------------------#
# This python file takes in multiple runs and calculate how Average   #
# Marginal Regret  changes as the app user percentage changes and the #
# simulation time elapses. The main execution is at the bottom of this#
# file.                                                               #
# NOTE: All "ND" refer to "Nash Distance," which is the old name of   #
#       average marginal regret. This will be fixed in later changes  #
#---------------------------------------------------------------------#

def generatePlot(percentage, timeStep, absNash, outputDir, plotEvent, eventStart, eventEnd, NDType = 'abs'):
  #-------------------------------------------------------------------#
  # percentage: Sorted list containing all app user percentages       #
  # timeStep: Time step for grouping vehicles                         #
  # absNash: Absolute Nash Distance                                   #
  # plotEven: Set true to plot two dash lines that mark the start and #
  #           end of events, specified by eventStart and eventEnd     #
  #-------------------------------------------------------------------#
  font = {'weight':'bold',
          'size':24}
  plt.rc('font', **font)
  fig, ax = plt.subplots(figsize = (24, 14), dpi = 100)

  #-------------------------------------------------------------------#
  # Change timestep into minutes from seconds                         #
  #-------------------------------------------------------------------#
  for i in range(len(timeStep)):
    timeStep[i] /= 60

  for i in range(len(percentage)):
    if NDType == 'abs':
      ax.plot(timeStep, absNash[i], color = (1 - float(percentage[i])/100, 0, float(percentage[i])/100), \
            label = '{}% App Users'.format(percentage[i]), \
            linewidth = 4.0)
    else:
      ax.plot(timeStep, absNash[i], color = (0, 1 - float(percentage[i])/100, float(percentage[i])/100), \
            label = '{}% App Users'.format(percentage[i]), \
            linewidth = 4.0)
    hand, lab = ax.get_legend_handles_labels()
    plt.legend(handles = hand, loc = 2)
  ax.set_xlabel('Elapsed Time (min)')
  if NDType == 'abs':
    ax.set_ylabel('Absolute Average Marginal Regret \n(sec)')
    ax.set_title('Absolute Average Marginal Regret for \nDifferent Percentages of App Users')
  else:
    ax.set_ylabel('Relative Average Marginal Regret \n(%)')
    ax.set_title('Relative Average Marginal Regret for \nDifferent Percentages of App Users')
  #-------------------------------------------------------------------#
  # Uncomment next line if you have to fix the upper/lower bounds of  #
  # the y-axis                                                        #
  #-------------------------------------------------------------------#
  #ax.set_xlim([0, 400])

  if plotEvent:
    ymin, ymax = plt.ylim()
    ax.plot([eventStart, eventStart], [ymin, ymax], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
    ax.plot([eventEnd, eventEnd], [ymin, ymax], color = (0, 0, 0), dashes = [2, 2], linewidth = 4.0)
  if NDType == 'abs':
    plt.savefig(outputDir + 'absND.png', dpi = 'figure')
  else:
    plt.savefig(outputDir + 'rltND.png', dpi = 'figure')

def extractSingleDB(fileName, thisPercentage, oriId, desId, maxT, minT, stepSize):
  #-------------------------------------------------------------------#
  # Extraction of a single SQLite database and calculate how absolute #
  # Nash Distance changes over time                                   #
  #                                                                   #
  # maxTime/minTime: Max/Min allowed time of entrance for vehicles    #
  # odiId/desId: id of desired origin/destination                     #
  #-------------------------------------------------------------------#
  print(('extracting database ' + fileName))

  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, entranceTime, (exitTime - entranceTime) FROM MIVEHTRAJECTORY WHERE exitTime != -1 AND entranceTime > {} AND entranceTime < {} AND origin = {} AND destination = {}'.format(minT, maxT, oriId, desId))
  vehTTime = cur.fetchall()
  con.close()

  tStepAccumTime = {}
  tStepAccumCount= {}
  tStepMinTime   = {}
  for i in range(len(vehTTime)):
    thisTStep = math.floor((vehTTime[i][1] - minT)/stepSize)
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
  for i in range(int(math.ceil((maxT - minT) / stepSize))):
    tStep.append(i * stepSize)
    if i in tStepMinTime:
      absNash.append(tStepAccumTime[i]/tStepAccumCount[i] - tStepMinTime[i])
      rltNash.append(100 * absNash[-1] * tStepAccumCount[i] / tStepAccumTime[i])
    else:
      absNash.append(0)
      rltNash.append(0)
  return tStep, absNash, rltNash

def sortBasedOnPercentage(percentage, absNash, rltNash):
  #-------------------------------------------------------------------#
  # Helper function to sort all data based on the percentage of app   #
  # users                                                             #
  #-------------------------------------------------------------------#
  zipped = list(zip(percentage, absNash, rltNash))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sAbsNash, sRltNash = list(map(list, unzip))
  return sPercentage, sAbsNash, sRltNash

def traverseMultiDB(fileList, maxTime, minTime, stepSize):
  #-------------------------------------------------------------------#
  # Traverse multiple SQLite DB and return how Absolute Nash Distance #
  # changes with time                                                 #
  #-------------------------------------------------------------------#
  percentage = []
  absNash    = []
  rltNash    = []
  tStep      = []
  oriId, desId  = getODPair(fileList[0])
  for filename in fileList:
    thisPercentage  = getPercentage(filename)
    thisTStep, thisAbsNash, thisRltNash = extractSingleDB(filename, thisPercentage, oriId, desId, maxTime, minTime, stepSize)
    percentage.append(thisPercentage)
    absNash.append(thisAbsNash)
    rltNash.append(thisRltNash)
    tStep = thisTStep
  percentage, absNash, rltNash = sortBasedOnPercentage(percentage, absNash, rltNash)
  return percentage, tStep, absNash, rltNash

def printUsage(): 
  print('usage: \n\t python std4_timeND.py directoryName maxEntranceTime minEntranceTime stepSize')
  print('\t directoryName: the directory in which the sqlite databases are stored')
  print('\t stepSize: the time step size for grouping vehicles, in seconds')
  print('try \n\t python std4_timeND.py ../sqliteDatabases/DemoBenchmarkAccident/ 14400 7200 600')
  sys.exit() 

def store2CSV(percentage, absND, runIdx, outputDir):
  outname = outputDir + 'run' + str(runIdx) + '_timeND.csv'
  with open(outname, 'w') as fout:
    for i in range(len(percentage)):
      fout.write(str(percentage[i]))
      for j in range(len(absND[i])):
        fout.write(',')
        fout.write(str(absND[i][j]))
      if i != (len(percentage) - 1):
        fout.write('\n')

# Main code starts here
if __name__ == '__main__':
  if len(sys.argv) != 5:
    printUsage()
  #-------------------------------------------------------------------#
  # Parsing input arguments and building list of all directories in   #
  # target (mother) directory                                         #
  #-------------------------------------------------------------------#
  dirList, outputDir, maxTime, minTime, stepSize = parseArgvTime(sys.argv, "timeAbsND")
  _, outputDirRlt, _, _, _ = parseArgvTime(sys.argv, "timeRltND")

  #-------------------------------------------------------------------#
  # Traverse, extract, and write data                                 #
  #-------------------------------------------------------------------#
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    percentage, timeStep, absNash, rltNash = traverseMultiDB(fileList, maxTime, minTime, stepSize)
    store2CSV(percentage, absNash, runIdx, outputDir)
    store2CSV(percentage, rltNash, runIdx, outputDirRlt)

  #-------------------------------------------------------------------#
  # Read data from csv file and plot                                  #
  #-------------------------------------------------------------------#
  percentage, timeStep, absNash = averageTimeND(outputDir, stepSize)
  generatePlot(percentage, timeStep, absNash, '../outputFigures/', True, 2*60, 4*60)
  percentage, timeStep, rltNash = averageTimeND(outputDirRlt, stepSize)
  generatePlot(percentage, timeStep, rltNash, '../outputFigures/', True, 2*60, 4*60, 'rlt')
