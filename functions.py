import paramiko
import scp
import time
import socket
import sys
import telnetlib
import os
import re
import hashlib
import RPi.GPIO as GPIO
import socket

# Current new used firmware versions
versionXW = "6.0.3"
versionXM = "6.0.3"
versionTI = "6.0.3"
versionWA = "8.3"
versionXC = "8.3"
swVersion = "1.7.0.4922887"
airgatewayfw = "AirGW.v1.1.9"

# Path to firmware
WAFirmware = "firmware/WA.v8.3.34573.170614.1646.bin"
AirGWFirmware = "firmware/AirGW.v1.1.9.30597.170329.1800.bin"
XWFirmware = ""
XMFirware = ""
TIFirmware = ""
XCFirmware = ""
ESFirmware = ""
ES10GFirmware = ""


socket.setdefaulttimeout(0.5)

user = "ubnt"
password = "ubnt"

printserver = "192.168.0.35"
switchHost = "192.168.1.13"
ip_hosts = ["192.168.1.1","192.168.1.2","192.168.1.20"]
SSHPort = 22
telnetPort = 23
printport = 5000

def buzzer():

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(33, GPIO.OUT)

    p = GPIO.PWM(33, 10000)  # channel=12 frequency=10000Hz

    p.start(50)

    while True:
        i = raw_input("Press enter to stop sound")
        if not i:
            break

    p.stop()
    GPIO.cleanup()

def check_server(address, port):
    # Create a TCP socket
    s = socket.socket()
    #print "Attempting to connect to %s on port %s" % (address, port)
    try:
        s.connect((address, port))
        #print "Connected to %s on port %s" % (address, port)
        return True
    except socket.error, e:
        #print "Connection to %s on port %s failed: %s" % (address, port, e)
        return False


def wait_for_host(host,port,step,timeout):
    counter = 0
    #print "Starting to wait for host\n"
    while (check_server(host,port) == False and counter <= timeout):
        time.sleep(step)
        counter += 1
        #print str(counter) + "\n"

    if counter >= timeout:
        return False
    else:
        return True


def switch_config(switchHost):
    # Enters config on a switch and returns the connection to be worked with
    
    if( not wait_for_host(switchHost,23,2,1000)):
        sys.exit('Problem with %s on port:%s') % (switchHost,23)

    tn = telnetlib.Telnet(switchHost)

    #For debugging
    #tn.set_debuglevel(9)

    tempvar = tn.read_until('\r\nUser:',5)
    if "User:" not in tempvar:
        sys.exit('Expecting login screen, gets this: ' + tempvar)

    tn.write(user.encode('ascii') + "\r\n")
    if password:
        tn.read_until('\r\nPassword:')
        tn.write(password.encode('ascii') + "\r\n")

    tn.write('enable\n')
    if password:
        tempvar = tn.read_until('\r\nPassword:', 5)
        if "Password:" in tempvar:
            tn.write(password.encode('ascii') + "\r\n")

    tn.write('config\n')

    return tn

def checkandupgrade(client,transferclient,tempvar):

    if not client:
        print "SSH connection not available"
        exit()

    if "XW" in tempvar:
        if versionXW in tempvar:
            return False
        else:
            print "transferring new firmware\n"
            transferclient.put('/srv/tftp/XWfirmware.bin', '/tmp/fwupdate.bin')

    elif "XM" in tempvar:
        if versionXM in tempvar:
            return False
        else:
            print "transferring new firmware\n"
            transferclient.put('/srv/tftp/XMfirmware.bin', '/tmp/fwupdate.bin')

    elif "XC" in tempvar:
        if versionXC in tempvar:
            return False
        else:
            print "transferring new firmware\n"
            transferclient.put('/srv/tftp/XCfirmware.bin', '/tmp/fwupdate.bin')

    elif "WA" in tempvar:
        if versionWA in tempvar:
            return False
        else:
            print "transferring new firmware\n"
            transferclient.put(WAFirmware, '/tmp/fwupdate.bin')

    elif "TI" in tempvar:
        if versionTI in tempvar:
            return False
        else:
            print "transferring new firmware\n"
            transferclient.put('/srv/tftp/TIfirmware.bin', '/tmp/fwupdate.bin')
    
    elif "AirGW" in tempvar:
        if airgatewayfw in tempvar:
            return False
        else:
            print "transferring new firmware\n"
            transferclient.put(AirGWFirmware, '/tmp/fwupdate.bin')
            
    else:
        print "This unit is not supported"
        print tempvar
        return False

    print "Done transferring, restarting unit\n"
    client.exec_command('/sbin/fwupdate -m')
    return True



def upgrade_link_firmware(port,linkHost):
    # Function use to upgrade firmware on ssh compatible hosts
    
    # Wait for host to be alive
    if( not wait_for_host(linkHost,22,2,1000)):
        print "Can't connect to ssh on switch port: %s!\n\n" % (port)
        return False

    # Connect to ssh and get version number
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(linkHost, username=user, password=password, look_for_keys=False, allow_agent=False)
    stdin, stdout, stderr = client.exec_command('cat /etc/version')
    tempvar = stdout.readline()

    # Open transfer variable
    transferclient = scp.SCPClient(client.get_transport())

    # Check if upgrade is needed and upgrade
    print "starting firmware check on port %s \n" % (port)
    if(checkandupgrade(client,transferclient,tempvar)):
        print "\n*******  Firmware upgraded  *******\n\n"
    else:
        print "\n*******  No need to upgrade on port %s   *******\n\n" % (port)

    transferclient.close()
    client.close()

    # Need to wait a bit so the device shuts down it's port before the next task
    time.sleep(4)


def open_port(tn,port):
    tn.write('interface 0/' + str(port) + '\n')
    tn.write('vlan pvid 1\n')

def close_port(tn,port):
    tn.write('interface 0/' + str(port) + '\n')
    tn.write('vlan pvid ' + str(port) + '\n')
    
    # Delete the arp instance to request new mac faster
    os.system("sudo arp -d 192.168.1.20")
    os.system("sudo arp -d 192.168.1.1")
    os.system("sudo arp -d 192.168.1.2")
    
    time.sleep(1)

def find_unit():

    for ip in ip_hosts:
        response = os.system("ping -c 1 " + ip + ">/dev/null")

        if response == 0:
            return ip
            
    return False

def switch_upgrade(ip):
    swHost = telnetlib.Telnet(ip)

    #For debugging
    #swHost.set_debuglevel(9)

    tempvar = swHost.read_until('\r\nUser:',5)
    if "User:" not in tempvar:
        sys.exit('Expecting login screen, gets this: ' + tempvar)

    swHost.write(user.encode('ascii') + "\r\n")
    if password:
        swHost.read_until('\r\nPassword:')
        swHost.write(password.encode('ascii') + "\r\n")

    swHost.write('enable\n')
    if password:
        tempvar = swHost.read_until('\r\nPassword:', 5)
        if "Password:" in tempvar:
            swHost.write(password.encode('ascii') + "\r\n")
    
    swHost.write('show hardware\n')
    serial = swHost.read_until('sdg',5)
    serial = re.search('Serial Number\.* (.+?)\n', serial)
    serial = serial.group(1)
    print (serial)

    swHost.write('show hardware\n')
    version = swHost.read_until('sgfd',5)
    version = re.search('Version\.*(.+?)\n', version)
    version = version.group(1)
    print (version)

    swHost.write('show hardware\n')
    model = swHost.read_until('sda',5)
    model = re.search('Model\.*(.+?)\n', model)
    model = model.group(1)
    print (model)

    if swVersion in version:
        print ("Correct firmware version\n\n")
    else:
        swHost.write('copy tftp://192.168.1.87/ES-eswh.v1.7.0.4922887.stk backup\n')
        swHost.read_until('(y/n)')
        swHost.write('y')

        print "Startet firmware transfer"

        swHost.read_until('successfully.')
        swHost.write('boot system backup\n')
        time.sleep(5)
        swHost.write('write memory\n')
        swHost.write('y')
        swHost.write('reload\n')
        swHost.read_until('(y/n)')
        swHost.write('y')

        swHost.close()


def just_upgrade(tn,portStart,portStop):

    for port in range(portStart,portStop+1):
        open_port(tn,port)

        ip = find_unit()
        while (ip == False):
            ip = find_unit()

        if check_server(ip,SSHPort):
            # Connect to ssh
            upgrade_link_firmware(port,ip)

        elif check_server(ip,telnetPort):
            switch_upgrade(ip)
        else:
            print ("Not SSH or telnet!\n")
            exit()

        close_port(tn,port)

def set_init(tn,portStart,portStop):
    
    for port in range(portStart,portStop+1):
        tn.write('interface 0/' + str(port) + '\n')
        tn.write('vlan pvid ' + str(port) + '\n')
        tn.write('poe opmode passive24v\n')


def get_ptmp_info():
    print ("")


def get_ptp_info():
    ptpName = raw_input("Enter descriptive name of this link:")
    ptpNameAP = ptpName + " AP"
    ptpNameSTA = ptpName + " STA"
    
    loop = True
    print "1. DHCP"
    print "2. Static IP (you need to know this)"

    while loop:
        choice = input("Enter 1 or 2: ")

        if choice==1:
            ptpStaticIP = False
            #loop = False
            print "Not implemented yet"
        elif choice==2:
            ptpStaticIP = True
            loop = False
            #print "Not implemented yet"
        else:
            print "Wrong input, try again!"

    if ptpStaticIP == True:
        ptpAPIP = raw_input("Enter ip-address of AP: ")
        ptpSTAIP = raw_input("Enter ip-address of STA: ")

    ssid = create_ssid_link()
    wpa = create_wpa_link()

    with open('config/p', 'r') as apfile:
        apfiledata = apfile.read()

    with open('config/p2', 'r') as stafile:
        stafiledata = stafile.read()

    apfiledata = apfiledata.replace('name=changeme','name=' + ptpNameAP)
    apfiledata = apfiledata.replace('ssid=changeme','ssid=' + ssid)
    apfiledata = apfiledata.replace('psk=changeme','psk=' + wpa)
    apfiledata = apfiledata.replace('ip=changeme','ip=' + ptpAPIP)

    stafiledata = stafiledata.replace('name=changeme','name=' + ptpNameSTA)
    stafiledata = stafiledata.replace('ssid=changeme','ssid=' + ssid)
    stafiledata = stafiledata.replace('psk=changeme','psk=' + wpa)
    stafiledata = stafiledata.replace('ip=changeme','ip=' + ptpSTAIP)


    with open('templateAP.cfg', 'w') as apfile:
        apfile.write(apfiledata)

    with open('templateSTA.cfg', 'w') as stafile:
        stafile.write(stafiledata)


def move_file_ssh(linkHost,file):
    
    if( not wait_for_host(linkHost,22,2,1000)):
        print "Can't connect to ssh!\n\n"
        return False

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(linkHost, username=user, password=password, look_for_keys=False, allow_agent=False)

    transferclient = scp.SCPClient(client.get_transport())

    transferclient.put(file, '/tmp/system.cfg')

    transferclient.close()
    client.close()

    return True


def apply_config(linkHost):


    if( not wait_for_host(linkHost,22,2,1000)):
        print "Can't connect to ssh!\n\n"
        return False

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(linkHost, username=user, password=password, look_for_keys=False, allow_agent=False)

    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdout = channel.makefile('rb')

    stdin.write('''
cd /tmp
save
reboot
''')
    print stdout.read()
    
    stdout.close()
    stdin.close()

#    stdin, stdout, stderr = client.exec_command('cd /tmp/ \n save \n reboot')
#    time.sleep(5)
#    stdin, stdout, stderr = client.exec_command('save')
#    time.sleep(5)
#    stdin, stdout, stderr = client.exec_command('reboot')
#    time.sleep(5)

    
    client.close()

def airgateway(tn):
    # Function to handle airgateway upgrade, config creation and apply config
    print ("nothing yet") 
    # What ports?
    portStart = int(input("The port to start with: "))
    portStop = int(input("The port to stop after: "))

    # Upgrade all units
    just_upgrade(tn,portStart,portStop)
    
    # What type of config? Bridge or fritidsnett
    loop = True
    print "1. Bridge"
    print "2. Fritidsnett"

    while loop:
        choice = input("Enter 1 or 2: ")

        if choice==1:
            bridgeMode = True
            loop = False
            #print "Not implemented yet"
        elif choice==2:
            bridgeMode = False
            #loop = False
            print "Not implemented yet"
        else:
            print "Wrong input, try again!"
            
    # If bridge, what bandwidth?
    if bridgeMode:
        # Open port then copy config g2
        for port in range(portStart,portStop+1):
            open_port(tn,port)
            move_file_ssh('192.168.1.1','config/g2')
            apply_config('192.168.1.1')
            close_port(tn,port)
    else:
        # Open port then copy config g
        for port in range(portStart,portStop+1):
            open_port(tn,port)
            create_airgateway_config()
            move_file_ssh('192.168.1.1','agtemp.cfg')
            apply_config('192.168.1.1')
            close_port(tn,port)
        
    
    # If fritidsnett, print labels
    
    # Move config and apply

def save_information(ssid,wpa,name,macaddress,ip):
    print ("later")
    
    
def print_airgw_label(ssid,wpa):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_socket.connect((printserver, printport))
    #print('Connecting ...')

    data = ssid + " | " + wpa
    client_socket.send(data)
    client_socket.close()
    
    
def create_airgateway_config():
    macaddress=subprocess.check_output("arp -a | grep 192.168.1.1 | awk '{print $4}' | head -1", shell=True)
    ssid="Telemixnett " + macaddress[9:17]
    wpa=create_wpa_airgw()
    
    with open('config/g', 'r') as gwfile:
        gwfiledata = gwfile.read()

    gwfiledata = gwfiledata.replace('ssid=changeme','ssid=' + ssid)
    gwfiledata = gwfiledata.replace('psk=changeme','psk=' + wpa)

    with open('agtemp.cfg', 'w') as gwfile:
        gwfile.write(gwfiledata)
        
    print_airgw_label(ssid,wpa)

        
def create_wpa_airgw():
    # More userfriendly with a 10 character key
    wpa = hashlib.md5(time.strftime("%S%M%H%d%m%y").encode('utf8')).hexdigest()[1:11]
    
    return wpa

def create_ssid_link():
    ssid = time.strftime("%H%M%d%m%Y", time.gmtime())

    return ssid

def create_wpa_link():
    
    wpa = hashlib.md5(time.strftime("%S%M%H%d%m%y").encode('utf8')).hexdigest()

    return wpa


def ptmp_menu():       ## Your menu design here
    print 30 * "-" , "MENU" , 30 * "-"
    print "1. Sektor"
    print "2. Sektor"
    print "3. Sektor"
    print "4. Sektor"
    print "5. Sektor"
    print "6. Sektor"
    print "7. Sektor"
    print "8. Sektor"
    print "9. Sektor"
    print "10. Sektor"
    print "11. Exit"
    print 67 * "-"


    loop=True

    while loop:          ## While loop which will keep going until loop = False
        print_menu()    ## Displays menu
        choice = input("Enter your choice [1-11]: ")

        if choice==1:
            print "has been selected"
            path = "STA.cfg"
        elif choice==2:
            print "has been selected"
            path = "STA.cfg"
        elif choice==3:
            print "has been selected"
            path = "STA.cfg"
        elif choice==4:
            print "has been selected"
            path = "STA.cfg"
        elif choice==5:
            print "has been selected"
            path = "A.cfg"
        elif choice==6:
            print "has been selected"
            path = "A.cfg"
        elif choice==7:
            print "has been selected"
            path = "B.cfg"
        elif choice==8:
            print "has been selected"
            path = "A.cfg"
        elif choice==9:
            print "has been selected"
            path = "A.cfg"
        elif choice==10:
            print "has been selected"
            path = "STA.cfg"
        elif choice==11:
            print "Menu 11 has been selected"
            ## You can add your code or functions here
            loop=False # This will make the while loop to end as not value of loop is set to False
        else:
            # Any integer inputs other than values 1-5 we print an error message
            raw_input("Wrong option selection. Enter any key to try again..")


