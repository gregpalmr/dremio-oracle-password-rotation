#!/usr/bin/env python
#
# SCRIPT:       rotate-dremio-oracle-password.py
#
# DESCRIPTION:  Change Dremio users' Oracle password for Oracle data sources. 
#
# USAGE:        python rotate-dremio-oracle-password.py
#
# AUTHOR:       greg@dremio.com
#
"""
  NOTES:        Step 1. Install Prerequisites:

                       a. Install Python 2.7.x
                                $ yum install -y python

                       b. Install Oracle Instant Client on RHEL 7 and CentOS 7
                                $ sudo yum localinstall -y \
                                       http://yum.oracle.com/repo/OracleLinux/OL7/oracle/instantclient/x86_64/getPackage/oracle-instantclient19.9-basiclite-19.9.0.0.0-1.x86_64.rpm
                                $ sudo yum install -y epel-release
                                $ sudo yum install -y python-pip
                                $ pip install cx_Oracle==7.3
				                $ pip install requests, json

               Step 2. Install this script on the Dremio Coordinator node:

                       a. Move this script to /usr/local/bin

                                $ mv rotate-dremio-oracle-password.py /usr/local/bin
                                $ chmod +x /usr/local/bin/rotate-dremio-oracle-password.py

                       b. Create an initial configuration file in /usr/local/etc/

                                $ cat <<EOF > /usr/local/etc/rotate-dremio-oracle-password.ini
                                 [main]
                                 dremio_server_url = http://localhost:9047
                                 dremio_admin_user = admin1
                                 dremio_admin_user_password = changeme123

                                 [oracle_source1]
                                 current_oracle_password = changeme1

                                 [oracle_source2]
                                 current_oracle_password = changeme2

                                 EOF

                                $ chmod go-rw /usr/local/etc/rotate-dremio-oracle-password.ini

                        c. Test it manually first, before scheduling it with cron

                                $ python rotate-dremio-oracle-password.py

               Step 3. Create a crontab entry to launch this script periodically.

                        a. This example runs the script every 29 days at 5:00AM

                                $ cat <<EOF > /etc/cron.d/rotate-dremio-oracle-password
                                # Run the Dremio Oracle Password Rotation program every 29 days
                                SHELL=/bin/bash
                                PATH=/sbin:/bin:/usr/sbin:/usr/bin
                                MAILTO="me@email.com"
                                0 5 */29 * * python /usr/local/bin/rotate-dremio-oracle-password.py > /var/log/rotate-dremio-oracle-password.log 2>&1
                                EOF

                                $ chmod go-rw /var/spool/cron/root

                        b. This example runs the script every 44 days at 5:00AM

                                $ cat <<EOF > /etc/cron.d/rotate-dremio-oracle-password
                                # Run the Dremio Oracle Password Rotation program every 29 days
                                SHELL=/bin/bash
                                PATH=/sbin:/bin:/usr/sbin:/usr/bin
                                MAILTO="me@email.com"
                                0 5 */44 * * python /usr/local/bin/rotate-dremio-oracle-password.py > /var/log/rotate-dremio-oracle-password.log 2>&1
                                EOF

                                $ chmod go-rw /var/spool/cron/root
"""

# Imports
#
import string, random
import datetime
import cx_Oracle
import requests, json
from ConfigParser import SafeConfigParser

# Constants
#
config_file = '/usr/local/etc/rotate-dremio-oracle-password.ini'

# Function Definitions
#
def logInfo(msg):
    print str(datetime.datetime.now()), ' - ' + msg

def logErr(msg):
    logInfo('ERROR: ' + msg)

def generate_password():

    password_length = 10

    password_characters = string.ascii_letters + string.digits + string.punctuation

    # convert printable from string to list and shuffle
    password_characters = list(password_characters)
    random.shuffle(password_characters)

    # generate random password and convert to string
    random_password = random.sample(password_characters, k=password_length)
    random_password = ''.join(random_password)

    return random_password

# Define Dremio login function
def loginToDremio(server_url, username, password):
    headers = {'content-type':'application/json'}
    login_data = {'userName': username, 'password': password}

    response = requests.post(server_url + '/apiv2/login', headers=headers, data=json.dumps(login_data), verify=False)

    if response.status_code is 200:

        logInfo ('Successfully authenticated with Dremio server: ' + server_url)

        data = json.loads(response.text)

        # retrieve the login token
        token = data['token']

        return {'content-type':'application/json', 'authorization':'_dremio{authToken}'.format(authToken=token)}
    else:
        logErr('Authentication failed with Dremio server: ' + serve_url)
        return ('')

# Read the config file and processing the Dremio data source definitions
#

logInfo(' Python program rotate-dremio-oracle-password.py has started')

config_parser = SafeConfigParser()
config_parser.read(config_file)

# First, process the [main] section
dremio_server_url =  config_parser.get('main', 'dremio_server_url')
dremio_admin_user =  config_parser.get('main', 'dremio_admin_user')
dremio_admin_user_password =  config_parser.get('main', 'dremio_admin_user_password')

#logInfo(' [main]')
#logInfo('     dremio_server_url = ' + dremio_server_url)
#logInfo('     dremio_admin_user = ' + dremio_admin_user)
#logInfo('     dremio_admin_user_password =  **********')

# Login to the Dremio server and process all the Oracle data sources
dremio_auth_headers = loginToDremio(dremio_server_url, dremio_admin_user, dremio_admin_user_password)

# Get a list of dremio catalog objects
response = requests.get(dremio_server_url + '/api/v3/catalog/', headers=dremio_auth_headers, verify=False)

if response.status_code is 200:
    logInfo ('Successfully queried the catalog.')
    #logInfo (response.content)
else:
    logInfo('Query catalog failed with reason: '+ str(response.content))

# Iterate through the json and pick out the ORACLE data source types
catalog_json = json.loads(response.text)

for item in catalog_json['data']:
    if item['containerType'] == 'SOURCE':
        source_id = item['id']

        # Check if this data source is an Oracle source
        response = requests.get(dremio_server_url + '/api/v3/catalog/' + source_id, headers=dremio_auth_headers, verify=False)

        source_json = json.loads(response.text)

        if source_json['type'] == 'ORACLE':
            source_name = source_json['name']
            logInfo('Processing Dremio data source ' + source_name + ' with id: ' + source_id)

            # Get the Oralce password for this data source from the config file
            current_oracle_password =  config_parser.get(source_name, 'current_oracle_password')
            if current_oracle_password == '':
                logError('    Failed to get Oracle password from config file for data source ' + source_name + '. Skipping this source.')
                continue

            oracle_hostname = source_json['config']['hostname']
            oracle_port     = source_json['config']['port']
            oracle_instance = source_json['config']['instance']
            oracle_username = source_json['config']['username']
            use_ssl         = source_json['config']['useSsl']

            logInfo('    Rotating Oracle password for data source ' + source_name)

            # Change the password in Oracle database
            try:
                oracle_connection = cx_Oracle.connect(oracle_username, current_oracle_password, oracle_hostname + "/" + oracle_instance)

                cursor = oracle_connection.cursor ()

                # generate new password
                new_password = generate_password()

                sqlCmd = 'ALTER USER ' + oracle_username + ' IDENTIFIED BY "' + new_password + '"'
                
                cursor.execute (sqlCmd)

                logInfo('    Oracle password successfully changed for Oracle user: ' + oracle_username)

                # Update the config file with the new password
                config_parser.set(source_name, 'current_oracle_password', new_password)

                # Update the Dremio data source with the new password
                data = '{"id": "266576bc-3d68-4f50-ba74-7b4ff2e4dce4","config": {"password": "' + new_password + '"}}'
                put_response = requests.put(dremio_server_url + '/api/v3/catalog/' + source_id, headers=dremio_auth_headers, data=data, verify=False)

                if response.status_code is 200:
                    logInfo ('    Successfully updated the Dremio data source with new password')
                else:
                    logError('    Failed to update the Dremio data source with new password - reason: ' + str(response.content))
 
            except cx_Oracle.DatabaseError as e:
                error, = e.args
                logErr ('    Failed to change Oracle password for Oracle user ' + oracle_username \
                    + ' on server: ' + oracle_hostname \
                    + '. Error Message: ' + error.message)

# Write the config file back to /usr/local/etc/rotate-dremio-oracle-password.ini
file_pointer = open(config_file, 'r+')
config_parser.write(file_pointer)
file_pointer.close()

logInfo(' Python program rotate-dremio-oracle-password.py has completed')         
# end of python script