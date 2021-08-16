#!/bin/python3

# https://github.com/jrester/tesla_powerwall
from tesla_powerwall import Powerwall
from ..lib import Constants

import pdb; pdb.set_trace()

# Create a simple powerwall object by providing the IP
powerwall = Powerwall(Constants.POWERWALL_IP)
#=> <Powerwall ...>

# Create a powerwall object with more options
"""
powerwall = Powerwall(
    endpoint="<ip of your powerwall>",
    # Configure timeout; default is 10
    timeout=10,
    # Provide a requests.Session
    http_sesion=None,
    # Whether to verify the SSL certificate or not
    verify_ssl=False,
    disable_insecure_warning=True,
    # Set the API to expect a specific version of the powerwall software
    pin_version=None
)
"""
#=> <Powerwall ...>

from tesla_powerwall import User

# Login as customer without email
# The default value for the email is ""
# powerwall.login("<password>")
#=> <LoginResponse ...>

# Login as customer with email
powerwall.login(POWERWALL_PASSWORD, POWERWALL_EMAIL)
#=> <LoginResponse ...>

# Login with different user
#powerwall.login_as(User.INSTALLER, "<password>", "<email>")
#=> <LoginResponse ...>

# Check if we are logged in
# This method only checks wether a cookie with a Bearer token exists
# It does not verify whether this token is valid
powerwall.is_authenticated()
#=> True

# Logout
powerwall.logout()

from tesla_powerwall import API

# Manually create API object
api = API(f'https://{POWERWALL_IP}/')
# Perform get on 'system_status/soe'
api.get_system_status_soe()
#=> {'percentage': 97.59281925744594}

# From existing powerwall
api = powerwall.get_api()
api.get_system_status_soe()

from tesla_powerwall import Version
# Pin powerwall object
#powerwall = Powerwall("<powerwall-ip>", pin_version="1.50.1")

# You can also pin a version after the powerwall object was created
#powerwall.pin_version("20.40.3")

powerwall.detect_and_pin_version()

powerwall.get_charge()
#=> 97.59281925744594


