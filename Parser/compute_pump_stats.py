#!/usr/bin/env python3.5
import argparse
import logging
import sys
import traceback
import Constants
import Mailer
import PumpStatsWriter
import TuyaLogParser

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description = "Compute waterpump stats and email alert")
  parser.add_argument('--always_email',
                      help    ='Send email report',
                      action  ='store_true',
                      default =False)
  parser.add_argument('--out_dir',
                      help    ='Folder for storing output files',
                      default ='%s/Junk/' % Constants.HOME)
  args = parser.parse_args()

  logfile = '%s/compute_pump_stats.txt' % args.out_dir
  log_format = '%(levelname)s:%(module)s.%(lineno)d:%(asctime)s: %(message)s'
  logging.basicConfig(filename=logfile, format=log_format, level=logging.DEBUG)
  logging.info('============')
  logging.info('Invoked command: %s' % ' '.join(sys.argv))

  try:
    for fileCounter in range(Constants.MAX_NEW_FILES):
      csvLogfile = Constants.TUYA_LOG_BASE
      csvLogfile += '.{}'.format(fileCounter) if fileCounter > 0 else ''
      csvLog = TuyaLogParser.TuyaLogParser(csvLogfile, Constants.JSON_SUMMARY_FILE)

    # Poll data is very coarse. Let's refine using event log.
    PumpStatsWriter.patchWithRachioEvents()

    # Gen Stats for the last N days.
    PumpStatsWriter.writeFromSummary()

    TuyaLogParser.genSendMessage(args.always_email)
  except Exception as e:
    msg="Something failed in script execution:\n%s" % traceback.format_exc()
    logging.error(msg)
    Mailer.sendmail(topic="[PumpStats]", alert=True, message=msg, always_email=True)
    raise

  logging.info('Done!')
  print("Done!")
