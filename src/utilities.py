import re
import os
from os import walk
import sqlite3
#---------------------------------------------------#
# File name in the following list will be neglected #
#---------------------------------------------------#
unwantedFileNames = ['hohoho.txt']
#---------------------------------------------------#
# The ids for non-app users and app-users           #
#---------------------------------------------------#
#appId       = 7995362
#nonAppId    = 7995363
appId = 53
nonAppId = 53

def parseArgv(argv, inputCall):
  inputCall = "/" + inputCall + "/"
  motherDir  = argv[1]
  maxTime  = int(argv[2])
  minTime  = int(argv[3])
  outputDir  = getOutputDir(motherDir, maxTime, minTime, inputCall)
  dirList    = [(x[0]+'/') for x in os.walk(motherDir)]
  dirList.remove(motherDir + '/')
  return dirList, outputDir, maxTime, minTime

def parseArgvTime(argv, inputCall):
  inputCall = "/" + inputCall + "/"
  motherDir  = argv[1]
  maxTime  = int(argv[2])
  minTime  = int(argv[3])
  stepSize = int(argv[4])
  outputDir  = getOutputDir(motherDir, maxTime, minTime, inputCall)
  dirList    = [(x[0]+'/') for x in os.walk(motherDir)]
  dirList.remove(motherDir + '/')
  return dirList, outputDir, maxTime, minTime, stepSize

def getRunIdx(dirName):
  dirName = dirName.split('/')
  dirName = dirName[len(dirName) - 2]
  runIdx  = int(re.search(r'\d+', dirName).group())
  return runIdx

def getAppNonAppId():
  return appId, nonAppId

def getColorChoices(unionKeys):
  #-----------------------------------------------------------#
  # Helper function for returning the ten color choices for   #
  # matplotlib, namely 'C0', 'C1', ..., and 'C9'              #
  #-----------------------------------------------------------#
  colors = []
  colors.append((1,0,0)) 
  colors.append((0,0,1)) 
  colors.append((0,1,0)) 
  colors.append((1,1,0)) 
  colors.append((0,1,1)) 
  colors.append((1,0,1))
  colorLookup = {}
  dummy = 0
  for i in unionKeys:
    colorLookup[i] = colors[dummy%6]
    dummy += 1
  return colorLookup

def getPercentage(longFileName):
  fileName = longFileName.split('/')
  fileName = fileName[-1]
  percentage = int(re.search(r'\d+', fileName).group())
  return percentage

def getKeyUnion(pathFlowList):
  unionKeys = set(pathFlowList[0].keys())
  for i in range(len(pathFlowList)):
    unionKeys = unionKeys.union(set(pathFlowList[i].keys()))
  if len(unionKeys) > 6:
    print('warning, number of paths exceed color choices (6), some paths might be mapped to the same color\n')
  return unionKeys

def mapKey2Int(keyUnion):
  keyLookup = {}
  dummy     = 0
  for i in keyUnion:
    keyLookup[i] = dummy
    dummy += 1
  return keyLookup

def buildVehPathDict(fileName):
  #-------------------------------------------------------------------#
  # Helper function to build a vehicle-path directory, with the path  #
  # specified by a list of numbers corresponding to the section ids in#
  # Aimsun                                                            #
  #-------------------------------------------------------------------#
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

def getNumVehicles(fileName, maxTime, minTime):
  #----------------------------------------------------------#
  # Get the number of vehicles in a database                 #
  #----------------------------------------------------------#
  # 862 = car_app class id, 863 = car_nonapp class id, this  #
  # part is incomplete because the classes are hard-coded,   #
  # should find way to solve this TODO Frank commented on 11/#
  # 17/2017                                                  #
  #appClassId    = 7995362
  #nonAppClassId = 7995363
  appClassId, nonAppClassId = getAppNonAppId()
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  # oid = object id, sid = class
  cur.execute('SELECT oid, sid FROM MIVEHTRAJECTORY WHERE (entranceTime > {} AND exitTime > 0 AND entranceTime < {})'.format(minTime, maxTime))
  rows = cur.fetchall()
  con.close()
  appCount    = 0
  nonAppCount = 0
  for row in rows:
    if row[1] == appClassId:
      appCount += 1
    else:
      nonAppCount += 1
  return appCount, nonAppCount

def getAllFilenames(dirName):
  #----------------------------------------------------------#
  # Helper function to traverse the given directory, returns #
  # a list of filenames                                      #
  #----------------------------------------------------------#
  f = []
  cwd = os.getcwd()
  for (dirpath, dirnames, filenames) in walk(dirName):
    f.extend(filenames)
  for i in range(len(unwantedFileNames)):
    if unwantedFileNames[i] in f:
      f.remove(unwantedFileNames[i])
  for i in range(len(f)):
    f[i] = dirName + f[i]
  return f

def getODPair(fileName):
  con = sqlite3.connect(fileName)
  cur = con.cursor()
  cur.execute('SELECT origin, destination FROM MIVEHTRAJECTORY')
  rows = cur.fetchall()
  con.close()
  currId  = 0
  idOdDict= {}
  idODict = {}
  idDDict = {}
  for row in rows:
    #thisSet = frozenset([row[0], row[1]])
    thisOD = [row[0], row[1]]
    if thisOD not in list(idOdDict.values()):
      idOdDict[currId] = thisOD
      idODict[currId]  = row[0]
      idDDict[currId]  = row[1]
      currId += 1
    del thisOD
  for key, value in list(idOdDict.items()):
    print(("\tOD: {}, corresponding number: {}".format(value, key)))
  desiredId = eval(input("please enter the corresponding number of your desired O/D\n"))
  print(("desired od is {}, {} <= note that the same od might have different corresponding numbers!".format(idODict[desiredId], idDDict[desiredId])))
  return idODict[desiredId], idDDict[desiredId]

def getOutputDir(dirName, maxT, minT, attribute): 
  dirName = dirName.split('/')
  if not os.path.exists('../outputCsvfiles/' + dirName[len(dirName) - 2] + '_OutputCSV_max_{}_min_{}'.format(maxT, minT) + attribute
):
    print(("created a directory ../outputCsvfiles/" + dirName[len(dirName) - 2] + '_OutputCSV_max_{}_min_{}'.format(maxT, minT) + attribute))
    os.makedirs('../outputCsvfiles/' + dirName[len(dirName) - 2] + '_OutputCSV_max_{}_min_{}'.format(maxT, minT) + attribute)
  outputDir = '../outputCsvfiles/' + dirName[len(dirName) - 2] + '_OutputCSV_max_{}_min_{}'.format(maxT, minT) + attribute
  return outputDir

def getOutputDirOld(dirName): 
  dirName = dirName.split('/')
  if not os.path.exists('../outputFigures/' + dirName[len(dirName) - 2] + '_OutputFigures'):
    print(("created a directory ./outputFigures/" + dirName[len(dirName) - 2] + '_OutputFigures'))
    os.makedirs('../outputFigures/' + dirName[len(dirName) - 2] + '_OutputFigures')
  outputDir = '../outputFigures/' + dirName[len(dirName) - 2] + '_OutputFigures'
  return outputDir
