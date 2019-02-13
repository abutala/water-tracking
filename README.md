# water-tracking and other IoT automata
Primary function:
IoT integration between Tuya smart switch and Rach.io irrigation control to track and alert on water consumption
* Poll data from Tuya and Rach.io
* Postprocessing to understand usage
* Http service for plotting data
* Email monitoring if current (short term filtered) rates exceed historical rates

Secondary function:
Simple script for monitoring Foscam IP cameras and Windows desktop, and reboot on demand with email reporting. Also manage ftp folder.

Ternary (still in experimentation):
Image classifier for garage door status with email reporting

Project Timelines:
* 08-10-2018: Initial concept for water-monitoring after n-th breakage of drip irrigation and many days of wasted water.
* 08-22-2018: Buy smart switches with energy monitoring (aka: Tuya)
* 08-25-2018: Energy monitor cli scraper tested
* 08-28-2018: Enhancements to tuya-cli to get electric current readings
* 08-30-2018: [v0.1]   Simple script to get csv logs of scrape, with a 3 step manual process to generate MS Excel plots.
* 09-03-2018: [v0.5]   1st online plot with canvasJS on apache server. "We have live data on pump state"
* 09-10-2018: [v0.6]   Harden: autostart polling script, crontabs, etc.
* 09-20-2018: [v0.8]   Plot histogram data. Looks good but not actionable. "May help find a leak"
* 10-06-2018: [v0.9]   Build rachio cli scraper. Plot rachio data. We now have full visibility on what is going on!
                       Actionable but not easy to understand. "Will help find a leak"
* 10-25-2018: [v1.0]   Plot "rates"! Actionable, easy to understand, but not accurate. "Will find leaks, but also high FA/MD"
* 11-01-2018: [v1.0.1] Build rachio event parser
* 11-04-2018: [v1.1]   Move to event parsing. "Definitive", but reactive.
* 11-06-2018: [v1.1.1] Better handling of missing events.
* 11-09-2018: [v1.2]   Emails. "Definitive with Reminders". Quick hack emails. Dropped the dummy zonestats.
                       Fix events handling for missing start event, or partial irrigation data by always starting RachioEvents reader from midnight.
* 11-16-2018: [v1.2.1] Refactor. Drop the low confidence data from short runs for Drip zones
* 11-17-2018: [v1.3]   Email alerts - 1st version. Seems to be about right, but will need tweaking. "Definitive and proactive"
* 11-21-2018: [v1.3.1] Refactor emails. Better handling of alerting, email frequency, content
* 12-08-2018: [v1.4]   Extend email capabilties. Add Foscam/Alpha monitoring to ecosystem. Refactor directories
* 12-08-2018: [v1.4.1] Use logger and arg parser in Parser. Remove symlink to lib files
* 01-15-2019: [v1.4.2] Github repo.
* 01-15-2019: [v1.4.3] Better filtering on email reports. Add pumpDutyCycle to emails.
* 01-20-2019: [v1.4.4] Better reporting on reboot. Add deep inspection to confirm windows is healthy
* 01-21-2019: [v1.5.0] Foscam garage image fetch. ML experimentation stubs.
                       Further refinement on email reports (inc script error traceback)
* 01-23-2019: [v1.5.1] HTML emails. CPU temp monitoring for host OS. Foscam ftp folder sanity check
* 01-25-2019: [v1.5.2] HTML emails part 2. Minor tweak to averaging computation. Installation notes for tensorflow
* 01-28-2019: [v1.5.3] Minor tweaks on plotter/email. bug fix on check_deep_state. restartable background processes in cron.
* 01-30-2019: [v1.5.4] Minor fix in rates computation. Post report on the website too. bug fixes on check_garage. Drop the non-alert day.
* 02-13-2019: [v1.5.5] Maintenance release. TF finally working.

--

Future:
* Foscam ML garage door check.

--

Dependencies:
* https://github.com/TuyaAPI/cli
* https://github.com/codetheweb/tuyapi
* wget -c https://nodejs.org/dist/latest-v10.x/node-v10.9.0-linux-arm64.tar.gz
* sudo tar -xzf node-v10.9.0-linux-arm64.tar.gz --strip-components=1 --group=root --no-same-owner -C /usr/local/
* apt-get install npm
* sudo npm -g i rachio
* sudo -H python3.6 -m pip install pyfoscam
* pip install tensorflow

Changes to libraries:
* In cli, modify get to passthrough config. Add support for dps option
* In tuyaApi, add support for dps option

Tensorflow install notes (Note: As of 1/1/2019, tf only available for python3.5, and not 3.6)
* Confirm that odroid has sufficent power (may fail if powered froma CPU usb port).
* If still hitting odroid reboots: cpulimit -l 10 -- <command>
* Increase system swap to 4GB.
** grep SwapTotal /proc/meminfo
** sudo swapoff -a
** sudo dd if=/dev/zero of=/swapfile bs=1G count=4
** sudo chmod 600 /swapfile
** sudo mkswap /swapfile
** sudo swapon /swapfile
* Finally did not use virtual env, but if required.
** sudo apt-get install virtualenv
** virtualenv --system-site-packages -p python3.5 ./python-tf/
* sudo apt update
* sudo apt upgrade
* sudo apt install gcc python3-dev python3-pip libxml2-dev libxslt1-dev zlib1g-dev g++
* Note: keras is a part of tf, but inorder to support legacy code, we need
** sudo apt-get install python3-pandas python3-numpy python3-scipy python3-tensorflow python3-keras
** \# And a ton more libraries that need to be installed to get the pip compiler to work
** sudo apt-get install libatlas-base-dev gfortran python-pip
* TF needed manual wheel download, and pip install
** wget https://github.com/lhelontra/tensorflow-on-arm/releases/download/v1.12.0/tensorflow-1.12.0-cp35-none-linux_aarch64.whl
** export CPATH=/usr/include/hdf5/serial/
** \# export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/aarch64-linux-gnu/hdf5/serial
** \# (Also add to /etc/ld.so.conf.d/libhdf5.conf && ldconfig --> did not work)
** HDF5_DIR=/usr/lib/x86_64-linux-gnu/hdf5/serial/ python3.5 -m pip install --upgrade h5py
** python3.5 -m pip install --upgrade tensorflow-1.12.0-cp35-none-linux_aarch64.whl
** python3.5 -m pip install scipy pandas

