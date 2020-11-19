# dremio-oracle-password-rotation

Change Dremio Data Lake Engine users' Oracle password for Oracle data sources. 

## Use this program to periodically rotate the Oracle password for users that are configured in your Dremio data sources.

### Step 1. Install Prerequisites:

a. Install Python 2.7.x

     $ yum install -y python

b. Install Oracle Instant Client on RHEL 7 and CentOS 7

     $ sudo yum localinstall -y \
                 http://yum.oracle.com/repo/OracleLinux/OL7/oracle/instantclient/x86_64/getPackage/oracle-instantclient19.9-basiclite-19.9.0.0.0-1.x86_64.rpm
     $ sudo yum install -y epel-release
     $ sudo yum install -y python-pip
     $ pip install cx_Oracle==7.3
     $ pip install requests, json

### Step 2. Install this script on the Dremio Coordinator node:

a. Move this script to /usr/local/bin

     $ mv rotate-dremio-oracle-password.py /usr/local/bin
     $ chmod +x /usr/local/bin/rotate-dremio-oracle-password.py

b. Create an initial configuration file in /usr/local/etc/

Because the Dremio REST API does not allow client programs to query the current Oracle password for a Dremio data source, this program keeps track of the current Oracle passwords in a seperate configuration file (.ini file). This script will generate new random passwords and will update this .ini file going forward.
       
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

### Step 3. Create a crontab entry to launch this script periodically.

a. This example runs the script every 29 days at 5:00AM

     $ cat <<EOF > /etc/cron.d/rotate-dremio-oracle-password
            # Run the Dremio Oracle Password Rotation program every 29 days
            SHELL=/bin/bash
            PATH=/sbin:/bin:/usr/sbin:/usr/bin
            MAILTO="me@email.com"
            0 5 */29 * * python /usr/local/bin/rotate-dremio-oracle-password.py >> /var/log/rotate-dremio-oracle-password.log 2>&1
            EOF

     $ chmod go-rw /etc/cron.d/rotate-dremio-oracle-password

b. This example runs the script every 44 days at 5:00AM

     $ cat <<EOF > /etc/cron.d/rotate-dremio-oracle-password
            # Run the Dremio Oracle Password Rotation program every 29 days
            SHELL=/bin/bash
            PATH=/sbin:/bin:/usr/sbin:/usr/bin
            MAILTO="me@email.com"
            0 5 */44 * * python /usr/local/bin/rotate-dremio-oracle-password.py >> /var/log/rotate-dremio-oracle-password.log 2>&1
            EOF

     $ chmod go-rw /etc/cron.d/rotate-dremio-oracle-password

---

Direct questions or comments to greg@dremio.com

