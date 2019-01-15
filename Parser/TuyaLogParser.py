#!/usr/bin/env python3.6
import collections
import csv
from enum import Enum
import json
import logging
import os
import Constants
import Mailer

class TuyaLogParser:
  ON_CURRENT_THRESH = 300

  def __init__(self, csvLogfile, jsonSummaryFile):
    self.email_errors = True # TODO: Feeble attempt to prevent a flood of email notifications.
    self.totalToggles = 0
    self.interStartMin = float('inf')
    self.totalPumpTime = 0
    self.logErrors = 0
    self.logStartEpoch = None
    self.logEndEpoch = None
    self.logStartTime = None
    self.logEndTime = None
    self.zonesStats = collections.defaultdict(lambda: {
                                               'zoneName' : '',
                                               'startEpochs' : [],
                                               'endEpochs' : [],
                                               'isOff' : True,
                                               'pumpRate' : float('nan'),
                                               'pumpTime': 0,
                                               'runTime' : 0,
                                               'toggles' : 0,
                                             })
    # Analyze the new log and update summary.json
    self.analyzeCsv(csvLogfile)
    self.writeSummaryFile(jsonSummaryFile)


  def analyzeCsv(self, csvLogfile):
    dataPoints, self.logErrors = loadCsv(csvLogfile)
    if (len(dataPoints) == 0):
      logging.error("Warn: No records in file %s. Ignoring..." % csvLogfile)
      Mailer.sendmail("[PumpStats]", alert=True, message="Log file empty. Polling issue", \
                      always_email=self.email_errors)
      self.email_errors = False
      return

    self.logStartTime = fetch(dataPoints[0], 'TIME')
    self.logStartEpoch = fetch(dataPoints[0], 'EPOCH', 'int')
    self.logEndTime = fetch(dataPoints[-1], 'TIME')
    self.logEndEpoch = fetch(dataPoints[-1], 'EPOCH', 'int')
    lastStartTime = fetch(dataPoints[0], 'EPOCH', 'int')
    prevEpoch = None
    prevZoneNum = None
    prevZoneStats = None
    interStartTime = float('inf')

    # Error Checking.
    if fetch(dataPoints[-1], 'CURRENT', 'int') < 0 or fetch(dataPoints[-1], 'ZONE_NUM', 'int') < -1:
      logging.warn("Warn: Data logging failure during polling at %s. Ignoring..." % self.logEndTime)
      Mailer.sendmail("[PumpStats]", alert=True, \
                      message="Data logging failure during polling: %s. Rate limited, or worse? " % self.logEndTime, \
                      always_email=self.email_errors)
      self.email_errors = False


    for record in dataPoints:
      try:
        currEpoch = fetch(record, 'EPOCH', 'int')
        currValue = fetch(record, 'CURRENT', 'int')
        currZoneNum = fetch(record, 'ZONE_NUM', 'int')
        currZoneStats = self.zonesStats[currZoneNum]
        currZoneStats['zoneName'] = fetch(record, 'ZONE_NAME')

        if (currZoneNum != prevZoneNum):
          currZoneStats['startEpochs'].append(currEpoch)
          if(prevZoneNum is not None):
            prevZoneStats['endEpochs'].append(currEpoch)
            prevZoneStats['isOff'] = True

        if prevEpoch is not None:
          currZoneStats['runTime'] += currEpoch - prevEpoch
          if not currZoneStats['isOff']:
            self.totalPumpTime += currEpoch - prevEpoch
            currZoneStats['pumpTime'] += currEpoch - prevEpoch
            interStartTime = 0
          if currZoneStats['isOff']:
            interStartTime += currEpoch - prevEpoch

        if (currValue > self.ON_CURRENT_THRESH and currZoneStats['isOff']):
          currZoneStats['isOff'] = False
          self.interStartMin = min(self.interStartMin, interStartTime)
          self.totalToggles += 1
          currZoneStats['toggles'] += 1
        elif (currValue < self.ON_CURRENT_THRESH and not currZoneStats['isOff']):
          currZoneStats['isOff'] = True

        prevZoneStats = currZoneStats
        prevZoneNum = currZoneNum
        prevEpoch = currEpoch
      except IndexError as e:
        logging.info("Failed to parse record: %s in file %s" % (record, self.csvLogfile))

    # Done looping through the file. Now compute average pumpRate in this window
    for zoneNum, zone in self.zonesStats.items():
      if (zone['runTime'] > 0):
        zone['pumpRate'] = float("%.04f" % (zone['pumpTime']/zone['runTime']))

    # Debug
    self.printLogStats(csvLogfile)


  def writeSummaryFile(self, jsonSummaryFile):
    if (len(self.zonesStats) <= 0):
      return

    summary = collections.defaultdict()
    try:
      summary = readSummaryFile(jsonSummaryFile)
    except:
      logging.warn('Warn: Failed to read old JSON file. Discarding ..')

    summary[self.logStartTime] = self.__dict__
    with open(jsonSummaryFile, 'w') as fp:
      fp.write(json.dumps(summary, sort_keys=True, indent=2))


  # User debug, pretty print some stats per log file processed
  def printLogStats(csvLog, csvLogfile):
    if (len(csvLog.zonesStats) < 1):
      return   # No Data

    logStartDate = csvLog.logStartTime[0:10]
    logStartDay = "" ## TODO: get day from startDate
    title = "{}   {} :: {} to {} [File Errors: {}]".format(
               csvLogfile, logStartDate[5:], csvLog.logStartTime[11:16],
               csvLog.logEndTime[11:16], csvLog.logErrors)
    logging.info(title)

    for zoneNum, zone in csvLog.zonesStats.items():
      logging.info("%25s - Toggles: %2d PumpTime: %s TotalTime: %s Rate: %.02f" %
              (zone['zoneName'], zone['toggles'],
               ("%2d:%02d" % divmod(zone['pumpTime'],60)),
               ("%3d:%02d" % divmod(zone['runTime'],60)),
               zone['pumpRate'])
           )


###################
##### Helpers #####
###################

# From a csv line record, fetch the column in TuyaLogCols and validate
class TuyaLogCols(Enum):
  EPOCH     = 1
  TIME      = 0
  CURRENT   = 2
  ZONE_NUM  = 3
  ZONE_NAME = 4
def fetch(record, enumVal, type = ''):
  index = TuyaLogCols[enumVal].value
  val = record[index]
  if (type == 'int'):
    try:
      val = int(val)
    except:
      val = -4
  return val


def loadCsv(csvLogfile):
  dataPoints = []
  logErrors = 0
  try:
    with open(csvLogfile, 'r', encoding='utf-8', errors='replace') as csv_file:
      csvReader = csv.reader((x.replace('\0','') for x in csv_file), delimiter=',')
      for record in csvReader:
        if (len(record) == len(TuyaLogCols)):
          dataPoints.append(record)
        else:
          logErrors += 1
  except IOError as e:
    logging.warn("Warn: Failed to load file: %s. Ignoring..." % csvLogfile)
  return [dataPoints, logErrors]


def readSummaryFile(jsonSummaryFile):
  with open(jsonSummaryFile) as fp:
    summary = json.load(fp)
  return summary


# Flag all zone where latest rate is greater than average of the last N days.
def genSendMessage():
  aggregated = collections.defaultdict(lambda: {'pumpTime': 0,
                                                'runTime': 0 })
  latest = collections.defaultdict(lambda: {'pumpRate': 0,
                                            'runTime': 0,
                                            'zoneName': "",
                                            'startTime': 0 })
  summary = readSummaryFile(Constants.JSON_SUMMARY_PATCH_FILE)

  for ts, record in sorted(summary.items())[-(Constants.DAYS_LOOKBACK*4):-1]:
    zonesStats = record['zonesStats']
    for zoneNumStr, zoneStats in zonesStats.items():
      pumpRate = zoneStats.get('pumpRate', 0)
      runTime = zoneStats.get('runTime', 0)
      latest[zoneNumStr]['pumpRate'] = pumpRate
      latest[zoneNumStr]['runTime'] = runTime
      latest[zoneNumStr]['startTime'] = record['logStartTime']
      latest[zoneNumStr]['zoneName'] = zoneStats.get('zoneName',"UNK")
      aggregated[zoneNumStr]['pumpTime'] += pumpRate*runTime
      aggregated[zoneNumStr]['runTime'] += runTime

  # Return a summary message.
  message = ""
  for zoneNumStr, zoneStats in sorted(latest.items()):
    average = aggregated[zoneNumStr]['pumpTime'] / aggregated[zoneNumStr]['runTime']
    if isInvalidDripData(zoneStats['zoneName'], zoneStats['runTime']):
      message += "Zone:%s Too short run on %s(%s) - Rate:%.03f Average:%.03f\n" \
                 % (zoneNumStr, zoneStats['startTime'], zoneStats['runTime'], zoneStats['pumpRate'], average)
    elif zoneStats['pumpRate'] < average * Constants.TRIGGER_THRESH:
      message += "Zone:%s Good on %s - Rate:%.03f Average:%.03f\n" \
                 % (zoneNumStr, zoneStats['startTime'], zoneStats['pumpRate'], average)
    elif zoneStats['pumpRate'] < Constants.IGNORE_BELOW_RATE:
      message += "Zone:%s Too low to detect on %s - Rate:%.03f Average:%.03f\n" \
                 % (zoneNumStr, zoneStats['startTime'], zoneStats['pumpRate'], average)
    else:
      message += "Zone:%s Failed check on %s (%s) - Rate:%.03f Average:%.03f\n" \
                 % (zoneNumStr, zoneStats['startTime'], zoneStats['runTime'], zoneStats['pumpRate'], average)

  logging.info(message)
  alert = True if "fail" in message.lower() else False
  Mailer.sendmail("[PumpStats]", alert, message)


# Hacky: Assumes only drip zones have "D" in 1st half of zoneName
def isInvalidDripData(zoneName, runTime):
  if runTime is None:
    runTime = 0
  return True if ('D' in zoneName.split('-')[0] and \
                    runTime < Constants.MIN_DRIP_REPORT_TIME) \
         else False
