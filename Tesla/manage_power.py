#!/usr/bin/env python3
# Uses TelsaPy written by Tim Dorssers
import argparse
import ast
from importlib import reload
import json
import logging
import os
import sys
import time
from typing import List, Optional
import Constants
import Mailer
import MyPushover
from TeslaPy.teslapy import Tesla, Vehicle, Battery, SolarPanel


def condition_matches(lhs, rhs, direction_up):
  if lhs > rhs and direction_up == True:
    # Gradient set for drain and okay to drain
    return True
  elif lhs < rhs and direction_up == False:
    # Grid charging needed
    return True
  return False


def average(my_list):
  return 0 if not my_list else sum(my_list)/len(my_list)


def extrapolate(my_list: List[float], time_sampling: float = 1) -> Optional[float]:
  # works only on reverse sorted.
  if not my_list:
    return None
  avg_diff = average([my_list[i] - my_list[i+1] for i in range(len(my_list) - 1)])
  return round(my_list[0] + avg_diff*time_sampling, 2)


def sanitize_pct(pct:float, historical_pcts: List[float], time_sampling: float) -> float:
  # Doesn't handle dynamicism on sleep_time very well. We should just store
  # epoch time in historical_pcts
  MAX_HISTORY = 5
  pct = round(pct, 2)
  updated_pct = pct
  if len(historical_pcts) >= MAX_HISTORY and (pct <= 0 or pct in historical_pcts):
    updated_pct = extrapolate(historical_pcts, time_sampling)
    updated_pct = round(max(min(updated_pct, 100), 0), 2)
  if updated_pct != pct:
    logging.warning(f"Got bad batt data:{pct}% Patched:{updated_pct:.2f}% from {historical_pcts} and continue..")
  if pct != 0:
    # This to prevent runaway extrapolation
    historical_pcts.insert(0, pct)
  else:
    # no choice
    historical_pcts.insert(0, updated_pct)
  if len(historical_pcts) > MAX_HISTORY:
    historical_pcts.pop()
  return updated_pct


def send_notification(msg):
  SMS_RCPT = Constants.POWERWALL_SMS_RCPT
  PUSHOVER_RCPT = Constants.POWERWALL_PUSHOVER_RCPT
  DO_SMS = False
  DO_PUSHOVER = True

  if DO_SMS:
    MyTwilio.sendsms(SMS_RCPT, msg)
  if DO_PUSHOVER:
    MyPushover.send_pushover(PUSHOVER_RCPT, msg)


def main(args):
  SMS_RCPT = Constants.POWERWALL_SMS_RCPT
  POLL_TIME_IN_SECS = Constants.POWERWALL_POLL_TIME
  try:
    with Tesla(args.email, verify=False, proxy=None, sso_base_url=None) as tesla:
      product = tesla.battery_list()[0]
      logging.info(f'{product["site_name"]} discovered')
      send_notification(f'Powerwall monitoring starting for site: {product["site_name"]}')
      loop_count = 0
      fail_count = 0
      sleep_time = 0
      historical_pcts = list()


      while True:
        loop_count += 1
        time.sleep(sleep_time)

        reload(Constants)
        currtime = time.localtime()
        POLL_TIME_IN_SECS = Constants.POWERWALL_POLL_TIME
        DECISION_POINTS = Constants.POWERWALL_DECISION_POINTS
        logging.info(f'Count {loop_count}')

        op_mode = None # APB: 5/25/23 seems we are no longer getting this data from the query

        try:
          product.get_site_info() # updates self
          product.get_site_data() # updates self
          logging.debug(json.dumps(product))

#          breakpoint()
          op_mode = product.get("operation") or op_mode
          backup_pct = product["backup_reserve_percent"]
          can_export = product["components"].get("customer_preferred_export_rule", "Not Found")
          can_grid_charge = not product["components"].get("disallow_charge_from_grid_with_solar_installed", False)
          assert (can_export == "battery_ok" and can_grid_charge), f"Error in PW config. Got export: {can_export}, grid_charge: {can_grid_charge}"

#          pct = product["energy_left"]/product["total_pack_energy"] * 100
          pct = product["percentage_charged"]
          pct = sanitize_pct(pct, historical_pcts, sleep_time/POLL_TIME_IN_SECS)
          future_pct = extrapolate(historical_pcts) or pct
          sleep_time = POLL_TIME_IN_SECS
          fail_count = 0
        except Exception as e:
          logging.warning(f"Failed repeatedly {fail_count} times with {e}. Discarding...")
          sleep_time = min(POLL_TIME_IN_SECS, 30) # Quick retry
          fail_count += 1
          if fail_count > 10:
            raise AssertionError(f"Continuously failing with {e}. Exiting..")
          continue
        logging.info(f"Read %:{pct:.2f}  Mode:{op_mode}  Export:{can_export}  Grid Charge:{can_grid_charge}")

        for point in DECISION_POINTS:
          currtime_val = currtime.tm_hour * 100 + currtime.tm_min
          # Rules are in strict precedence. Find the first rule that applies.
          if currtime_val >= point.time_start and currtime_val < point.time_end:
            hrs_to_end = (int(point.time_end/100) - currtime.tm_hour) + \
                    (point.time_end%100 - currtime.tm_min) / 60 - currtime.tm_sec / 3600
            trigger_now_pct = round(point.pct_thresh - (point.pct_gradient_per_hr * hrs_to_end), 2)
            trigger_next_pct = round(trigger_now_pct + point.pct_gradient_per_hr * (sleep_time/3600), 2)

            logging.info(f"{pct=:.2f} {trigger_now_pct=:.2f} // {future_pct=:.2f} {trigger_next_pct=:.2f} for {point.reason}")
            if condition_matches(pct, trigger_now_pct, point.iff_higher):
              # Rule applies. Send command if needed. Do not process further
              logging.info(f"Matched {pct} with {trigger_now_pct}%: {point.reason}")
              status = status2 = None
              if op_mode != point.op_mode:
                status = product.set_operation(point.op_mode)
                op_mode = point.op_mode
              desired_min = point.pct_min
              if point.pct_min_trail_stop:
                # Avoids unnecessary battery drain during change cycle
                desired_min = backup_pct
                while pct >= desired_min + point.pct_min_trail_stop:
                  desired_min += point.pct_min_trail_stop
              if backup_pct != desired_min:
                status2 = product.set_backup_reserve_percent(int(desired_min))
#              if status or status2:
              if status2: ## can't trigger off status any more
                status += f" {point.op_mode}"
                status2 += f" {desired_min}%"
                msg = f"At:{pct}%, {point.reason}  Mode:{status}  Reserve:{status2}"
                logging.warning(msg)
                if args.send_notification or point.always_notify:
                  send_notification(msg)
                else:
                  logging.info("SMS send skipped due to config flags")
              break  # out of for loop
            elif condition_matches(future_pct, trigger_next_pct, point.iff_higher):
              logging.warning(f"Matched future {future_pct} with {trigger_next_pct}%: {point.reason} Fast retry.. ")
              sleep_time = min(POLL_TIME_IN_SECS, 60)
              break  # out of for loop
            else:
              logging.info(f"In time window, but skip: Trig:{trigger_now_pct}% {point.reason}")
        else:
          logging.warning(f"Matched no rule. Is that okay?")

  except EnvironmentError as e:
    logging.error(f"Oops. Telsa token expired? Run gui.py direclty from TeslaPy. Error: {e}")
    send_notification("Oops. Telsa token expired? Run gui.py direclty from TeslaPy")
  except Exception as e:
    import traceback
    logging.error(e)
    logging.error(traceback.print_exc())
    send_notification(e.__repr__())
  logging.error(f"Will hard exit after delay of 3600 seconds to prevent respawn churn...\n\n\n\n\n")
  time.sleep(3600) # Don't quit early, as we'll just keep respawning
  return


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Tesla Owner API CLI')
  parser.add_argument('-d', '--debug', action='store_true',
                       help='set logging level to debug')
  parser.add_argument('-e', dest='email', help='login email', default=Constants.POWERWALL_EMAIL)
  parser.add_argument('-k', dest='keyvalue', help='API parameter (key=value)',
            action='append', type=lambda kv: kv.split('=', 1))
  parser.add_argument('-q','--quiet', action='store_true', help="Don't print to stdout")
  parser.add_argument('--send_notification',
                      help  = 'Send notification using Twilio or Pushover',
                      action  = 'store_true')

  args = parser.parse_args()

  logfile = '%s/%s.log' % (Constants.LOGGING_DIR, os.path.basename(__file__))
  log_format = '%(levelname)s:%(module)s.%(lineno)d:%(asctime)s: %(message)s'
  logging.basicConfig(filename=logfile, format=log_format, level=logging.INFO)
  if args.debug:
      logging.getLogger().setLevel(logging.DEBUG)
  if not args.quiet:
      logging.getLogger().addHandler(logging.StreamHandler())
  logging.info('============')
  logging.info('Invoked command: %s' % ' '.join(sys.argv))

  main(args)

  logging.warn(f"Exiting..\n\n")
