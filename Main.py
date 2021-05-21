import sys
import paramiko
from paramiko import SSHClient
from scp import SCPClient
import os
import time
import datetime
from tqdm import tqdm
import subprocess
import socket

path = ''
global_coach_list = []


class TCMSMan:
    """
    Class TCMSMan aka the velociraptor of downloads, will sort after the infamous TCMS logs in record time.
    Using wild Jurasic python object programming, together we can overcome the pain that is TCMS!

    Author:     Ben McGuffog, Fleet Support Engineer
    Version:    2020-Dec

    """

    def __init__(self):
        self.cpg_dict = {
            # SEATED
            "15001": "10.128.33.1", "15002": "10.128.34.1", "15003": "10.128.35.1",
            "15004": "10.128.36.1", "15005": "10.128.37.1", "15006": "10.128.38.1",
            "15007": "10.128.39.1", "15008": "10.128.40.1", "15009": "10.128.41.1",
            "15010": "10.128.42.1", "15011": "10.128.43.1",
            # TEST
            # "pi": "172.24.22.246",
        }

    def get_CPG_address(self, coach):
        """
        Returns the CPG dictionary item for the argument coach.
        Will cast int arguments to strings.
        :param coach:
        :return self.cpg_dict.get(coach):
        """
        if type(coach) is int:
            coach = str(coach)

        return self.cpg_dict.get(coach)

    def get_local_IP_list(self):
        return socket.gethostbyname_ex(socket.gethostname())[2]

    def get_logs(self, coach):
        """
        Automatically downloads the log files from the TCMS HMI.
        Utilises the ssh port 22 protocols.
        :param coach:
        :return none:
        """
        global path
        username = 'ftp_guest'
        password = 'ftpguest'
        host = self.get_CPG_address(coach)
        port = 22
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        TCMS_Files = ['/home/traintic/etc/MVBVarDesc.xml',
                      '/home/traintic/etc/HMIAlarms.xml',
                      '/var/traintic/log/AlarmReg00']

        # Attempt an scp connection to the host and get the logs for TCMS
        for TCMS_File in TCMS_Files:
            try:
                client.connect(host, port, username, password)
                self.make_log_dir(coach)
                # This is a little bit of a hack. SCPClient doesn't allow you to pass a wild
                # character to the string, it just sees it as a literal character.
                # Sanitize gets around this with lambda magic.
                with SCPClient(client.get_transport(), sanitize=lambda x: x, progress=TCMSMan.progress) as scp:
                    scp.get(TCMS_File, path)
                scp.close()
            except paramiko.ssh_exception.NoValidConnectionsError:
                print("Failed connection to " + str(coach))
                TCMSMan.write_to_log_file("paramiko.ssh_exception occurred for " + str(coach))

    def get_rake_ids(self, coaches):
        """
        Iterates through a list of coaches and calls the getLogs for each.
        :param coaches:
        :return none:
        """
        for coach in coaches:
            self.get_logs(coach)

    def make_list_of_coaches(self):
        """
        Creates a list of coaches from the CPS list that are currently reachable.
        :return none:
        """
        global global_coach_list
        global_coach_list.clear()
        print("""

        ........................................................................................................  
        .%%%%%%..%%%%%....%%%%...%%%%%%..%%..%%...%%%%...%%%%%....%%%%...%%%%%%..%%%%%%..%%%%%%..%%..%%...%%%%..
        ...%%....%%..%%..%%..%%....%%....%%%.%%..%%......%%..%%..%%..%%....%%......%%......%%....%%%.%%..%%.....
        ...%%....%%%%%...%%%%%%....%%....%%.%%%...%%%%...%%%%%...%%..%%....%%......%%......%%....%%.%%%..%%.%%%.
        ...%%....%%..%%..%%..%%....%%....%%..%%......%%..%%......%%..%%....%%......%%......%%....%%..%%..%%..%%.
        ...%%....%%..%%..%%..%%..%%%%%%..%%..%%...%%%%...%%.......%%%%.....%%......%%....%%%%%%..%%..%%...%%%%..
        ........................................................................................................  

        """)
        for coach in tqdm(self.cpg_dict.keys()):
            if self.is_coach_reachable(coach, self.get_CPG_address(coach)):
                global_coach_list.append(coach)
                TCMSMan.write_to_log_file("Downloaded: " + str(coach) + " at: " + str(self.get_CPG_address(coach)))
        
        if not self.local_IP_address_is_good():
            print(ASCII.devil())
            print("Your IP laptop address should start with 10.128.X.X")
            input('Your laptop IP addresses are ' + str(self.get_local_IP_list()) + ' Press ENTER key to exit')
            exit()

    def local_IP_address_is_good(self):
        local_ip_list = self.get_local_IP_list()
        for ip_address in self.cpg_dict.values():
            if ip_address[:9] in local_ip_list:
                return True
        return False

    @staticmethod
    def make_log_dir(coach):
        """
        Attempts to make a local directory for the current download session.
        Returns the new folder as a string if successful, else returns None.
        :param coach:
        :return none:
        """
        global path
        path = 'logs/' + str(coach) + '/' + str(time.strftime('%Y%m%d', time.localtime()))
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            print('Creation of the directory %s has failed' % path)
            TCMSMan.write_to_log_file('Creation of the directory %s has failed' % path)
        else:
            print('Successfully uploaded logs to %s ' % path)
            TCMSMan.write_to_log_file('Successfully uploaded logs to %s ' % path)

    @staticmethod
    def is_coach_reachable(coach_number, coach_IP):
        """
        Returns true if coach is currently reachable.
        :param coachNumber:
        :param coachIP:
        :return boolean:
        """
        response = not subprocess.call('ping -n 1 -w 100 ' + str(coach_IP), stdout=subprocess.PIPE)
        if response:
            TCMSMan.write_to_log_file(str(coach_number) + " contact confirmed at " + str(coach_IP))
        return response

    @staticmethod
    def write_to_log_file(log_name):
        """
        Writes to a logfile named TCMSMan_logfile.txt.
        :param log_name:
        :return none:
        """
        try:
            f = open("TCMSMan_logfile.txt", "a")
            f.write(str(datetime.datetime.utcnow().strftime("%b%d-%H:%M:%S.%f")[:-4]) + " " + log_name + "\n")
            f.close()
        except OSError:
            print("Failed to write to TCMSMan_logfile.txt")
            pass

    @staticmethod
    def progress(filename, size, sent):
        """
        Define progress callback that prints the current percentage completed for the file
        :param filename:
        :param size:
        :param sent:
        :return none:
        """
        sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent) / float(size) * 100))

class ASCII:
    @classmethod
    def dino(cls):
        dino_splash = """







                    ──────────────────████████
                    ─────────────────███▄███████
                    ─────────────────███████████
                    ─────────────────███████████
                    ─────────────────██████
                    ─────────────────█████████
                    ───────█───────███████
                    ───────██────████████████
                    ───────███──██████████──█
                    ───────███████████████
                    ───────███████████████
                    ────────█████████████
                    ─────────███████████
                    ───────────████████
                    ────────────███──██
                    ────────────██────█
                    ────────────█─────█
                    ────────────██────██
                TCMS Man Version 3.1 Raptor Distro 
              Author: Ben McGuffog, Support Engineer

        """
        return dino_splash

    @classmethod
    def devil(cls):
        devil_splash = """





        Ψσυ нλƲε λπɢεгεd ƬςΜЅ Μλπ
                                          _.---**""**-.       
                                  ._   .-'           /|`.     
                                   \`.'             / |  `.   
                                    V              (  ;    \  
                                    L       _.-  -. `'      \ 
                                   / `-. _.'       \         ;
                                  :   ¢Λƒ      __   ;    _   |
         Are you even connected   :`-.___.+-*"': `  ;  .' `. |
              to the train?       |`-/     `--*'   /  /  /`.\|
                         \        : :              \    :`.| ;
                          \       | |   .           ;/ .' ' / 
                                  : :  / `             :__.'  
                                   \`._.-'       /     |      
                                    : )         :      ;      
                                    :----.._    |     /       
                                   : .-.    `.       /        
                                    \     `._       /         
                                    /`-            /          
                                   :             .'           
                                    \ )       .-'             
                                     `-----*"'     

        Try connecting to T4 of the Train Switch
        Try setting your IP address to 10.128.33.10, mask 255.224.0.0
        Try setting you IP address to automatic. 

        """

        return devil_splash


def main():
    """
    Instantiates a class object of type TCMSMan and makes a list of ping-able coaches.
    Using this list, each coach is then sent an SCP protocol to download the logs from the
    the respective TCMS file locations and save them to the local machine.
    :return None:
    """
    global global_coach_list
    getRakeLogs = TCMSMan()
    getRakeLogs.make_list_of_coaches()
    if global_coach_list:
        print('Search complete. Found: ' + ', '.join(global_coach_list))
        getRakeLogs.get_rake_ids(global_coach_list)
        print(ASCII.dino())
        print('****** Logs gathered for: ' + ', '.join(global_coach_list))
    else:
        print(ASCII.devil())

    input("Press ENTER key to exit")


if __name__ == "__main__":
    main()
