from os import walk
from utilities import getAllFilenames, getKeyUnion
import sys
import matplotlib.pyplot as plt
import numpy as np

def averageND(targetDir):
  fileNames = getAllFilenames(targetDir)
  count = {}
  absND = {}
  rltND = {}
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        line.strip()
        thisLine = line.split(',')
        if int(thisLine[0]) not in list(absND.keys()):
#          count[int(thisLine[0])] = 1
          absND[int(thisLine[0])] = [float(thisLine[1])]
          rltND[int(thisLine[0])] = [float(thisLine[2])]
        else:
#          count[int(thisLine[0])] += 1
          absND[int(thisLine[0])].append(float(thisLine[1]))
          rltND[int(thisLine[0])].append(float(thisLine[2]))
  absnd = []
  absndStd = []
  rltnd = []
  rltndStd = []
  percentage = []
  for key in list(absND.keys()):
#    absnd.append(absND[key]/count[key])
#    rltnd.append(rltND[key]/count[key])
    percentage.append(key)
    absnd.append(np.mean(np.array(absND[key])))
    absndStd.append(np.std(np.array(absND[key])))
    rltnd.append(np.mean(np.array(rltND[key])))
    rltndStd.append(np.std(np.array(rltND[key])))
  zipped = list(zip(percentage, absnd, rltnd, absndStd, rltndStd))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sAbsND, sRltND, sAbsNDStd, sRltNDStd = list(map(list, unzip))
  return sPercentage, sAbsND, sRltND, sAbsNDStd, sRltNDStd

def parseLinePathTTime(line):
  line.strip()
  line = line.split(',')
  percentage = int(line[0])
  i = 1
  retDict = {}
  while i < len(line):
    retDict[int(line[i])] = [float(line[i+1])]
    i += 2
  return percentage, retDict

def averagePathTTime(targetDir):
  fileNames = getAllFilenames(targetDir)
  # Key: percentage, Item: dictionary of pathID - flow/count
  # PathFlow:
  #   key                  item
  #   10               {33665: 151,
  #                     33625: 7}
  #   30               {33625: 84}
  pathFlow = {}
  pathCount= {}
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        curPercentage, curDict = parseLinePathTTime(line)
        if curPercentage not in list(pathFlow.keys()):
          pathFlow[curPercentage] = curDict
#          pathCount[curPercentage]= {}
#          for pathID in list(curDict.keys()):
#            pathCount[curPercentage][pathID] = 1
        else:
          for pathID in list(curDict.keys()):
            if pathID not in list(pathFlow[curPercentage].keys()):
              pathFlow[curPercentage][pathID] = [curDict[pathID][0]]
#              pathCount[curPercentage][pathID]= 1
            else:
              pathFlow[curPercentage][pathID].append(curDict[pathID][0])
#              pathCount[curPercentage][pathID]+= 1
#  print(pathFlow)
  pathFlowStd = {}
  for percentage in list(pathFlow.keys()):
    pathFlowStd[percentage] = {}
    for pathID in list(pathFlow[percentage].keys()):
      pathFlowStd[percentage][pathID] = np.std(np.array(pathFlow[percentage][pathID]))
      pathFlow[percentage][pathID] = np.mean(np.array(pathFlow[percentage][pathID]))
#  print(pathFlow)
#  print(pathFlowStd)
  percentage = []
  flowList   = []
  stdList    = []
  for key in list(pathFlow.keys()):
    percentage.append(key)
    flowList.append(pathFlow[key])
    stdList.append(pathFlowStd[key])
  unionKeys = getKeyUnion(flowList)
  zipped = list(zip(percentage, flowList, stdList))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sPercentFlowDict, sPercentFlowStdDict = list(map(list, unzip))
  return sPercentage, sPercentFlowDict, sPercentFlowStdDict, unionKeys

def parseLinePathFlow(line):
  line.strip()
  line = line.split(',')
  percentage = int(line[0])
  i = 1
  retDict = {}
  while i < len(line):
    retDict[int(line[i])] = float(line[i+1])
    i += 2
  return percentage, retDict

def averagePathflow(targetDir):
  fileNames = getAllFilenames(targetDir)
  # Key: percentage, Item: dictionary of pathID - flow/count
  # PathFlow:
  #   key                  item
  #   10               {33665: 151,
  #                     33625: 7}
  #   30               {33625: 84}
  pathFlow = {}
  pathCount= {}
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        curPercentage, curDict = parseLinePathFlow(line)
        if curPercentage not in list(pathFlow.keys()):
          pathFlow[curPercentage] = curDict
          pathCount[curPercentage]= {}
          for pathID in list(curDict.keys()):
            pathCount[curPercentage][pathID] = 1
        else:
          for pathID in list(curDict.keys()):
            if pathID not in list(pathFlow[curPercentage].keys()):
              pathFlow[curPercentage][pathID] = curDict[pathID]
              pathCount[curPercentage][pathID]= 1
            else:
              pathFlow[curPercentage][pathID] += curDict[pathID]
              pathCount[curPercentage][pathID]+= 1
  print(pathFlow)
  print(pathCount)
  for percentage in list(pathFlow.keys()):
    for pathID in list(pathFlow[percentage].keys()):
      pathFlow[percentage][pathID] /= pathCount[percentage][pathID]
  percentage = []
  flowList   = []
  for key in list(pathFlow.keys()):
    percentage.append(key)
    flowList.append(pathFlow[key])
  unionKeys = getKeyUnion(flowList)
  print(unionKeys)
  zipped = list(zip(percentage, flowList))
  zipped.sort()
  unzip  = list(zip(*zipped))
  sPercentage, sPercentFlowDict = list(map(list, unzip))
  return sPercentage, sPercentFlowDict, unionKeys

def tokenize(line):
  line.strip()
  line = line.split(',')
  percent = int(line[0])
  timeSeries = [float(x) for x in line[1:-1]]
  return percent, timeSeries

def averageTimeND(targetDir, stepSize):
  fileNames = getAllFilenames(targetDir)
  percentage = []
  timeStep   = []
  absNash    = []
  count      = []
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        thisPercent, thisSeries = tokenize(line)
        if thisPercent not in percentage:
          percentage.append(thisPercent)
          absNash.append(thisSeries)
          count.append(1)
        else:
          idx = percentage.index(thisPercent)
          for i in range(len(absNash[idx])):
            absNash[idx][i] += thisSeries[i]
          count[idx] += 1
  for i in range(len(percentage)):
    absNash[i] = [x/count[i] for x in absNash[i]]
  for i in range(len(absNash[0])):
    timeStep.append(i * stepSize)
  return percentage, timeStep, absNash

def tokenizePathFlow(line):
  line.strip()
  line = line.split(',')
  percent = int(line[0])
  path    = int(line[1])
  timeSeries = [float(x) for x in line[2:-1]]
  return percent, path, timeSeries

def getDesiredPath(fileNames):
  possiblePath = {}
  pathFlowCount= {}
  pathNum      = 0
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        thisPercent, thisPath, thisSeries = tokenizePathFlow(line)
        thisPathFlow = sum(thisSeries)
        if thisPath not in list(possiblePath.keys()):
          possiblePath[thisPath] = pathNum
          pathFlowCount[thisPath]= thisPathFlow
          pathNum += 1
        else:
          pathFlowCount[thisPath] += thisPathFlow
  for key, value in list(possiblePath.items()):
    if pathFlowCount[key] > 50:
      print(("\tpath: {}, corresponding number: {}, flow: {}".format(key, value, pathFlowCount[key])))
  desiredPath = eval(input("please enter desired path:\n"))
  desiredPathHash = 0
  for key, value in list(possiblePath.items()):
    if value == desiredPath:
      desiredPathHash = key
      break
  return desiredPathHash

def averageTimePathFlow(targetDir):
  fileNames = getAllFilenames(targetDir)
  desiredPath = getDesiredPath(fileNames)
  percentage = []
  timeStep   = []
  absNash    = []
  count      = []
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        thisPercent, thisPath, thisSeries = tokenizePathFlow(line)
        if thisPath != desiredPath:
          continue
        elif thisPercent not in percentage:
          percentage.append(thisPercent)
          absNash.append(thisSeries)
          count.append(1)
        else:
          idx = percentage.index(thisPercent)
          for i in range(len(absNash[idx])):
            absNash[idx][i] += thisSeries[i]
          count[idx] += 1
  for i in range(len(percentage)):
    absNash[i] = [x/count[i] for x in absNash[i]]
  scale = 600
  for i in range(len(absNash[0])):
    timeStep.append(i * scale)
  return percentage, timeStep, absNash, desiredPath

def getDesiredPathStd6(fileNames):
  possiblePath = {}
  pathFlowCount= {}
  pathNum      = 0
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        thisPercent, thisPath, thisSeries = tokenizePathFlow(line)
        thisPathFlow = sum(thisSeries)
        if thisPath not in list(possiblePath.keys()):
          possiblePath[thisPath] = pathNum
          pathFlowCount[thisPath]= thisPathFlow
          pathNum += 1
        else:
          pathFlowCount[thisPath] += thisPathFlow
  for key, value in list(possiblePath.items()):
      print(("\tpath: {}, corresponding number: {}, flow: {}".format(key, value, pathFlowCount[key])))
  desiredPathHash = eval(input("please enter desired path:\n"))
  return desiredPathHash

def getDesiredPathStd6Old(fileNames):
  possiblePath = {}
  pathFlowCount= {}
  pathNum      = 0
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        thisPercent, thisPath, thisSeries = tokenizePathFlow(line)
        thisPathFlow = sum(thisSeries)
        if thisPath not in list(possiblePath.keys()):
          possiblePath[thisPath] = pathNum
          pathFlowCount[thisPath]= thisPathFlow
          pathNum += 1
        else:
          pathFlowCount[thisPath] += thisPathFlow
  for key, value in list(possiblePath.items()):
      print(("\tpath: {}, corresponding number: {}, flow: {}".format(key, value, pathFlowCount[key])))
  desiredPathIdx = eval(input("please enter desired path:\n"))
  desiredPathHash = 0
  for key, value in list(possiblePath.items()):
    if value == desiredPathIdx:
      desiredPathHash = key
  return desiredPathHash

def averageTimePathTimeOld(targetDir):
  fileNames = getAllFilenames(targetDir)
  print(fileNames)
  hashKey   = getDesiredPathStd6Old(fileNames)
  percentage = []
  timeStep   = []
  absNash    = []
  count      = {}
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        thisPercent, thisPath, thisSeries = tokenizePathFlow(line)
        if thisPath != hashKey:
          continue
        elif thisPercent not in percentage:
          percentage.append(thisPercent)
          absNash.append(thisSeries)
          dummy = []
          for number in thisSeries:
            if number == 0:
              dummy.append(0)
            else:
              dummy.append(1)
          count[thisPercent] = dummy
        else:
          idx = percentage.index(thisPercent)
          for i in range(len(absNash[idx])):
            absNash[idx][i] += thisSeries[i]
          for i in range(len(thisSeries)):
            if thisSeries[i] != 0:
              count[thisPercent][i] += 1
  for i in range(len(percentage)):
    dummySeries = []
    for j in range(len(count[percentage[i]])):
      if count[percentage[i]][j] != 0:
        dummySeries.append(absNash[i][j] / count[percentage[i]][j])
      else:
        dummySeries.append(0)
    absNash[i] = dummySeries
  scale = 600
  for i in range(len(absNash[0])):
    timeStep.append(i * scale)
  return percentage, timeStep, absNash


def averageTimePathTime(targetDir, hashKey):
  print(targetDir)
  fileNames = getAllFilenames(targetDir)
  percentage = []
  timeStep   = []
  absNash    = []
  count      = []
  for fileName in fileNames:
    with open(fileName, 'r') as fin:
      for line in fin:
        thisPercent, thisPath, thisSeries = tokenizePathFlow(line)
        if thisPath != hashKey:
          continue
        elif thisPercent not in percentage:
          percentage.append(thisPercent)
          absNash.append(thisSeries)
          count.append(1)
        else:
          idx = percentage.index(thisPercent)
          for i in range(len(absNash[idx])):
            absNash[idx][i] += thisSeries[i]
          count[idx] += 1
  for i in range(len(percentage)):
    absNash[i] = [x/count[i] for x in absNash[i]]
  scale = 600
  for i in range(len(absNash[0])):
    timeStep.append(i * scale)
  return percentage, timeStep, absNash

