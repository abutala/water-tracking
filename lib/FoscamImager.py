#!/usr/bin/env python3
from foscam.foscam import FoscamCamera, FOSCAM_SUCCESS
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import io
import logging
import time
import Constants
import NetHelpers

def print_ipinfo(returncode, params):
  if returncode != FOSCAM_SUCCESS:
    print('Failed to get IPInfo!')
    return
  print('IP: %s, Mask: %s' % (params['ip'], params['mask']))

class FoscamImager:
  def __init__(self, nodeIP, display_images=False):
    self.mycam = FoscamCamera(Constants.FOSCAM_NODES['Garage'], 88, \
               Constants.FOSCAM_USERNAME, Constants.FOSCAM_PASSWORD)
    self.display_images = display_images
    self.count = 0
    if display_images:
      plt.ion()
      plt.tight_layout()

  def reset_errcount():
    self.count = 0

  def getImageBytes(self):
    with NetHelpers.no_stdout():
      picture_data = self.mycam.snap_picture_2()
#     (retVal, IPparams) = self.mycam.get_ip_info(print_ipinfo)
#     logging.debug("Got IP params: %s" % json.dumps(IPparams))

    if (len(picture_data) < 2 or picture_data[1] is None):
      self.count += 1
      raise Exception("[%s] No data in image file, or no image returned. Count = %d\n" % (ts, self.count))
    imgBytes = picture_data[1]
    return imgBytes

  def getImage(self, filename=None):
    currtime = time.localtime()
    ts = time.strftime("%Y-%m-%d_%H-%M-%S", currtime)
    logging.info("Updating at %s" % ts)

    imgBytes  = self.getImageBytes()
    img = mpimg.imread(io.BytesIO(imgBytes), format='JPG')
    if self.display_images == True:
      plt.imshow(img)
      plt.show()
      plt.pause(0.001)
      if filename is not None:
        with open(filename, "wb") as fh:
          fh.write(imgBytes) ## Ubuntu: Use "eog <filename>" to view
        logging.info("Saved image to %s" % filename)
    return img
