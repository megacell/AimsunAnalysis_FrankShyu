import sqlite3
import sys
import os
import csv
import datetime
import re
import debugMessage as dm
import numpy as np
import matplotlib.pyplot as plt
from utilities import *
from averageCSVFiles import *
#---------------------------------------------------------------------#
# This python file takes in multiple runs and calculate how Average   #
# Marginal Regret/Relative Average Marginal Regret changes as the app #
# user percentage changes. The main execution is at the bottom of this#
# file.                                                               #
# NOTE: All "ND" refer to "Nash Distance," which is the old name of   #
#       average marginal regret. This will be fixed in later changes  #
#---------------------------------------------------------------------#

def generatePlot(Percentage, AbsND, RltND, AbsNDStd, RltNDStd):
  #-------------------------------------------------------------------#
  # Percentage: Sorted list containing all app user percentages       #
  # AbsND/RltND: Average of Absolute/Relative Nash Distance           #
  # AbsNDStd/RltNDStd: Standard deviation of data points              #
  #-------------------------------------------------------------------#
  font = {'weight':'bold',
          'size':24}
  plt.rc('font', **font)

  fig, ax1 = plt.subplots(figsize = (24, 14), dpi = 100)
  ax1.set_xlabel('Percentage of App Users (%)')
  ax1.set_ylabel('Absolute Average Marginal Regret (sec)')
  ax1.errorbar(Percentage, AbsND, yerr = AbsNDStd, color = (0,0,1), label = 'Absolute Average Marginal Regret', dashes=[2,2], linewidth = 5.0, fmt='--o', ecolor='b', capsize=5.0, capthick=5.0)
  ax1.grid(color = (0,0,1), linestyle = '--', linewidth = 2)
  #-------------------------------------------------------------------#
  # Uncomment next line if you have to fix the upper/lower bounds of  #
  # the y-axis                                                        #
  #-------------------------------------------------------------------#
  #ax1.set_ylim([100, 220])

  ax2      = ax1.twinx()
  ax2.set_ylabel('Relative Average Marginal Regret (%)')
  ax2.errorbar(Percentage, RltND, yerr = RltNDStd, color = (1, 0, 0), label = 'Relative Average Marginal Regret', dashes = [10, 5, 2, 5], linewidth = 5.0, ecolor='r', capsize=5.0, capthick=5.0)
  ax2.set_yticks(np.linspace(ax2.get_yticks()[0], ax2.get_yticks()[-1], len(ax1.get_yticks())))

  plt.title('Average Marginal Regret')
  hand1, lab1 = ax1.get_legend_handles_labels()
  hand2, lab2 = ax2.get_legend_handles_labels()
  firstLegend = plt.legend(handles = hand1, loc = 3)
  dummy       = plt.gca().add_artist(firstLegend)
  plt.legend(handles = hand2, loc = 1)

  plt.savefig('../outputFigures/percentage-ND.png', dpi = 'figure')

def extractSingleDB(fileName, maxTime, minTime, oriId, desId):
  #-------------------------------------------------------------------#
  # Extraction of a single SQLite database and calculate the Absolute/#
  # Relative Nash Distance                                            #
  #                                                                   #
  # maxTime/minTime: Max/Min allowed time of entrance for vehicles    #
  # odiId/desId: id of desired origin/destination                     #
  #-------------------------------------------------------------------#
  print(('extracting database ' + fileName))
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT oid, sid, entranceTime, exitTime FROM MIVEHTRAJECTORY WHERE (entranceTime > {} AND exitTime > 0 AND entranceTime < {} AND origin = {} AND destination = {})'.format(minTime, maxTime, oriId, desId))
  rows = cur.fetchall()
  con.close()

  numVeh      = 0
  totalTTime  = 0
  minTTime    = float(1000000000)
  for row in rows:
    thisTTime = float((row[3] - row[2]))
    numVeh   += 1
    totalTTime += thisTTime
    if thisTTime < minTTime:
      minTTime = thisTTime

  #-------------------------------------------------------------------#
  # Absolute Nash Distance                                            #
  #        = \frac{1}{n} \sum_{i=1}^{n} (agentTime - minTime)         #
  #        = avgAgentTime - minTime                                   #
  # Relative Nash Distance                                            #
  #        = absND / (avgAgentTime)                                   #
  #-------------------------------------------------------------------#
  absNashDistance = totalTTime/numVeh - minTTime
  rltNashDistance = 100 * absNashDistance * numVeh/totalTTime
  return absNashDistance, rltNashDistance

def sortBasedOnPercentage(percentage, absND, rltND):
  #-------------------------------------------------------------------#
  # Helper function to sort all data based on the percentage of app   #
  # users                                                             #
  #-------------------------------------------------------------------#
  zipped = list(zip(percentage, absND, rltND))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sAbsND, sRltND = list(map(list, unzip))
  return sPercentage, sAbsND, sRltND

def traverseMultiDB(fileList, maxTime, minTime):
  #-------------------------------------------------------------------#
  # Traverse multiple SQLite DB and return the Absolute/Relative Nash #
  # Distance                                                          #
  #-------------------------------------------------------------------#
  percentage = []
  absNashDistance = []
  rltNashDistance = []
  oriId, desId = getODPair(fileList[0])

  for filename in fileList:
    thisPercentage = getPercentage(filename)
    thisAbsNashDistance, thisRltNashDistance \
      = extractSingleDB(filename, maxTime, minTime, oriId, desId)
    percentage.append(thisPercentage)
    absNashDistance.append(thisAbsNashDistance)
    rltNashDistance.append(thisRltNashDistance)

  percentage, absNashDistance, rltNashDistance \
    = sortBasedOnPercentage(percentage, absNashDistance, rltNashDistance)
  return percentage, absNashDistance, rltNashDistance

def printUsage(): 
  print('usage: \n\t python std1_percentND.py directoryName maxEntranceTime minEntranceTime')
  print('\t directoryName: the directory in which the sqlite databases are stored')
  print('try \n\t python std1_percentND.py ../sqliteDatabases/DemoBenchmarkAccident/ 14400 7200')
  sys.exit() 

def store2CSV(percentage, absND, rltND, runIdx, outputDir):
  outname = outputDir + 'run' + str(runIdx) + '_ND.csv'
  with open(outname, 'w') as fout:
    for i in range(len(percentage)):
      fout.write(str(percentage[i]) + ',' + str(absND[i]) + ',' + str(rltND[i]))
      if i != (len(percentage) - 1):
        fout.write('\n')

if __name__ == '__main__':
  if len(sys.argv) != 4:
    printUsage()
  #-------------------------------------------------------------------#
  # Parsing input arguments and building list of all directories in   #
  # target (mother) directory                                         #
  #-------------------------------------------------------------------#
  dirList, outputDir, maxTime, minTime = parseArgv(sys.argv, "percentND")

  #-------------------------------------------------------------------#
  # Traverse, extract, and write data                                 #
  #-------------------------------------------------------------------#
  for dirName in dirList:
    runIdx   = getRunIdx(dirName)
    fileList = getAllFilenames(dirName)
    dm.printObjFiles(fileList, True)
    percentage, absND, rltND = traverseMultiDB(fileList, maxTime, minTime)
    store2CSV(percentage, absND, rltND, runIdx, outputDir)

  #-------------------------------------------------------------------#
  # Read data from csv file, calculate standard deviation, and plot   #
  #-------------------------------------------------------------------#
  percentage, absND, rltND, absNDStd, rltNDStd = averageND(outputDir)
  generatePlot(percentage, absND, rltND, absNDStd, rltNDStd)
