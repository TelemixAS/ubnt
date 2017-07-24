import paramiko
import scp
import time
import socket
import sys
import telnetlib
import os
from functions import *

switchHost = "192.168.1.13"


SSHPort = 22
telnetPort = 23

user = "ubnt"
password = "ubnt"

#portStart = 2
#portStop = 8

def print_menu():       ## Your menu design here
    print (30 * "-" , "MENU" , 30 * "-")
    print ("1. PTP Link")
    print ("2. Just upgrade")
    print ("3. PTMP")
    print ("4. Airgateway config")
    print ("5. Exit")
    print (67 * "-")
  


def main():

    # Open telnet session to switch Host and enter global config
    tn = switch_config(switchHost)

    #just_upgrade(tn,portStart,portStop)
    
    loop=True      
  
    while loop:          ## While loop which will keep going until loop = False
        print_menu()    ## Displays menu
        choice = input("Enter your choice [1-5]: ")
     
        
        if choice==1:     
            # Change this menu option, can be better and use existing functions
            
            print ("Menu 1 has been selected")
            print ("AP needs to be in port 2 and STA needs to be in port 3!")
            get_ptp_info()
            open_port(tn,2)
            upgrade_link_firmware(2,'192.168.1.20')
            if( not wait_for_host('192.168.1.20',SSHPort,2,1000)):
                #print "Can't connect to ssh on switch port: %s!\n\n" % (port)
                print ("Wait error after firmware")
                return False
            
            move_file_ssh('192.168.1.20','templateAP.cfg')
            apply_config('192.168.1.20')
            close_port(tn,2)


            open_port(tn,3)
            upgrade_link_firmware(3,'192.168.1.20')
            if( not wait_for_host('192.168.1.20',SSHPort,2,1000)):
                #print "Can't connect to ssh on switch port: %s!\n\n" % (port)
                print ("Wait error after firmware")
                return False

            move_file_ssh('192.168.1.20','templateSTA.cfg')
            apply_config('192.168.1.20')
            close_port(tn,3)
            
            buzzer()
            ## You can add your code or functions here
        elif choice==2:
            print ("Menu 2 has been selected")
            
            portStart = int(input("The port to start with: "))
            portStop = int(input("The port to stop after: "))
            
            just_upgrade(tn,portStart,portStop)
            
            buzzer()
            ## You can add your code or functions here
        elif choice==3:
            print ("Menu 3 has been selected, this will only create the config for antennas, not Gateways. Use nr 4 for that!")
            lines = []
            portStart = int(input("The port to start with: "))
            portStop = int(input("The port to stop after: "))
            
            with open("config/.gitignore") as file:
                for line in file:
                    line in line.strip()
                    lines.append(line)
            
            
            confirm = False
            config_choice = raw_input("What config/site do you want on these devices? (all devices will get this config) :")
            while confirm == False:
                yn=raw_input("Is this correct? " + config_choice +" Y/n")
                while yn.lower() not in "y,n":
                    yn=raw_input("Press y or n")
                if yn.lower() == "y":
                    confirm = True
                else:
                    print("Try again")
                    config_choice = raw_input("What config/site do you want on these devices? (all devices will get this config) :")
            
            
            config_path = "config/" + config_choice
            
            just_upgrade(tn,portStart,portStop)
            for port in range(portStart,portStop+1):
                open_port(tn,port)
                move_file_ssh('192.168.1.20',config_path)
                apply_config('192.168.1.20')
                close_port(tn,port)
                
            ## You can add your code or functions here
        elif choice==4:
            print ("Menu 4 has been selected")
            airgateway(tn)
            ## You can add your code or functions here
        elif choice==5:
            print ("Menu 5 has been selected")
            ## You can add your code or functions here
            loop=False # This will make the while loop to end as not value of loop is set to False
        else:
            # Any integer inputs other than values 1-5 we print an error message
            raw_input("Wrong option selection. Enter any key to try again..")

if __name__ == "__main__":
    main()
