#!/usr/bin/env python3.5

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import Constants
import Mailer


#### Main Routine ####
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description = "Speedtest and External IP detection utility`")
  parser.add_argument('--always_email',
                      help    ='Send email report',
                      action  ='store_true',
                      default =False)
  args = parser.parse_args()

  logfile = '%s/%s.log' % (Constants.LOGGING_DIR, os.path.basename(__file__))
  log_format = '%(levelname)s:%(module)s.%(lineno)d:%(asctime)s: %(message)s'
  logging.basicConfig(filename=logfile, format=log_format, level=logging.INFO)
  logging.info('============')
  logging.info('Invoked command: %s' % ' '.join(sys.argv))

  msg=""
  cmd = "/usr/bin/speedtest -f json"
  alert = True
  count = 0
  msg = ""
  while (alert and count < Constants.MAX_RETRIES):
    count += 1
    try:
      out = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT, shell=False,
          universal_newlines=True, timeout=600)
      payload = json.loads(out)
      dlW_mbps = payload.get("download", {}).get("bandwidth", 0)*8/1024/1024
      ulW_mbps = payload.get("upload", {}).get("bandwidth", 0)*8/1024/1024
      ext_ip = payload.get("interface", {}).get("externalIp", "UNK")
      if (dlW_mbps > Constants.MIN_DL_BW and ulW_mbps > Constants.MIN_UL_BW):
          msg += "Link good: "
          alert = False
      elif (dlW_mbps > Constants.MIN_DL_BW * 0.8 and ulW_mbps > Constants.MIN_UL_BW * 0.8):
          msg += "Link degraded (>80%): "
      else:
          msg += "Link bad (<80%): "
      msg += "[%s] DL: %.1f Mbps UL: %.1f Mbps\n" % (ext_ip, dlW_mbps, ulW_mbps)
      time.sleep(120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
      msg += e.output

  logging.info(msg)
  Mailer.sendmail(topic="[SpeedTest]", message=msg, \
          always_email=args.always_email, alert=alert)
  print(msg)
  print("Done")

