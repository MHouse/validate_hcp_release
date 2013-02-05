#! /usr/bin/env python
__author__ = 'mhouse01'
import ConfigParser

config = ConfigParser.ConfigParser()

# When adding sections or items, add them in the reverse order of
# how you want them to be displayed in the actual file.
# In addition, please note that using RawConfigParser's and the raw
# mode of ConfigParser's respective set functions, you can assign
# non-string values to keys internally, but will receive an error
# when attempting to write to a file or when you get it in non-raw
# mode. SafeConfigParser does not allow such assignments to take place.
config.add_section('Credentials')
config.set('Credentials', 'username', 'user_example')
config.set('Credentials', 'password', 'pass_example')

config.add_section('Server')
config.set('Server', 'server', 'server.domain.org')
config.set('Server', 'security', 'off')

# Writing our configuration file to 'validate_hcp_release.cfg'
with open('validate_hcp_release.cfg', 'wb') as configfile:
    config.write( configfile )
