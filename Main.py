import sys
import paramiko
from paramiko import SSHClient
from scp import SCPClient
import os
import time
import datetime
from tqdm import tqdm
import subprocess

path = ''
coachList = []


class TCMSMan:
    """
    Class TCMSMan aka the velociraptor of downloads, will sort after the infamous TCMS logs in record time.
    Using wild Jurasic python object programming, together we can overcome the pain that is TCMS!

    Author:     Ben McGuffog, Fleet Support Engineer
    Version:    2020-Dec

    """

    def __init__(self):
        self.cpgdict = {
            # SEATED
            "15001": "10.128.33.1", "15002": "10.128.34.1", "15003": "10.128.35.1",
            "15004": "10.128.36.1", "15005": "10.128.37.1", "15006": "10.128.38.1",
            "15007": "10.128.39.1", "15008": "10.128.40.1", "15009": "10.128.41.1",
            "15010": "10.128.42.1", "15011": "10.128.43.1",
            # TEST
            # "pi": "172.24.22.246",
        }

    def getCPGAddress(self, coach):
        """
        Returns the CPG dictionary item for the argument coach.
        Will cast int arguments to strings.
        :param coach:
        :return self.cpgdict.get(coach):
        """
        if type(coach) is int:
            coach = str(coach)

        return self.cpgdict.get(coach)

    def getLogs(self, coach):
        """
        Automatically downloads the log files from the TCMS HMI.
        Utilises the ssh port 22 protocols.
        :param coach:
        :return none:
        """
        global path
        username = 'ftp_guest'
        password = 'ftpguest'
        host = self.getCPGAddress(coach)
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
                self.makeLogDir(coach)
                # This is a little bit of a hack. SCPClient doesn't allow you to pass a wild
                # character to the string, it just sees it as a literal character.
                # Sanitize gets around this with lambda magic.
                with SCPClient(client.get_transport(), sanitize=lambda x: x, progress=TCMSMan.progress) as scp:
                    scp.get(TCMS_File, path)
                scp.close()
            except paramiko.ssh_exception.NoValidConnectionsError:
                print("Failed connection to " + str(coach))
                TCMSMan.writeToLogfile("paramiko.ssh_exception occurred for " + str(coach))

    def getRake(self, coaches):
        """
        Iterates through a list of coaches and calls the getLogs for each.
        :param coaches:
        :return none:
        """
        for coach in coaches:
            self.getLogs(coach)

    def makeCoachList(self):
        """
        Creates a list of coaches from the CPS list that are currently reachable.
        :return none:
        """
        global coachList
        coachList.clear()
        print("""

        ........................................................................................................  
        .%%%%%%..%%%%%....%%%%...%%%%%%..%%..%%...%%%%...%%%%%....%%%%...%%%%%%..%%%%%%..%%%%%%..%%..%%...%%%%..
        ...%%....%%..%%..%%..%%....%%....%%%.%%..%%......%%..%%..%%..%%....%%......%%......%%....%%%.%%..%%.....
        ...%%....%%%%%...%%%%%%....%%....%%.%%%...%%%%...%%%%%...%%..%%....%%......%%......%%....%%.%%%..%%.%%%.
        ...%%....%%..%%..%%..%%....%%....%%..%%......%%..%%......%%..%%....%%......%%......%%....%%..%%..%%..%%.
        ...%%....%%..%%..%%..%%..%%%%%%..%%..%%...%%%%...%%.......%%%%.....%%......%%....%%%%%%..%%..%%...%%%%..
        ........................................................................................................  

        """)
        for coach in tqdm(self.cpgdict.keys()):
            if self.isCoachReachable(coach, self.getCPGAddress(coach)):
                coachList.append(coach)
                TCMSMan.writeToLogfile("Downloaded: " + str(coach) + " at: " + str(self.getCPGAddress(coach)))

    @staticmethod
    def makeLogDir(coach):
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
            TCMSMan.writeToLogfile('Creation of the directory %s has failed' % path)
        else:
            print('Successfully uploaded logs to %s ' % path)
            TCMSMan.writeToLogfile('Successfully uploaded logs to %s ' % path)

    @staticmethod
    def isCoachReachable(coachNumber, coachIP):
        """
        Returns true if coach is currently reachable.
        :param coachNumber:
        :param coachIP:
        :return boolean:
        """
        response = not subprocess.call('ping -n 1 -w 100 ' + str(coachIP), stdout=subprocess.PIPE)
        if response:
            TCMSMan.writeToLogfile(str(coachNumber) + " contact confirmed at " + str(coachIP))
        return response

    @staticmethod
    def writeToLogfile(logString):
        """
        Writes to a logfile named TCMSMan_logfile.txt.
        :param logString:
        :return none:
        """
        try:
            f = open("TCMSMan_logfile.txt", "a")
            f.write(str(datetime.datetime.utcnow().strftime("%b%d-%H:%M:%S.%f")[:-4]) + " " + logString + "\n")
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


def main():
    """
    Instantiates a class object of type TCMSMan and makes a list of ping-able coaches.
    Using this list, each coach is then sent an SCP protocol to download the logs from the
    the respective TCMS file locations and save them to the local machine.
    :return None:
    """
    global coachList
    getRakeLogs = TCMSMan()
    getRakeLogs.makeCoachList()
    if coachList:
        print('Search complete. Found: ' + ', '.join(coachList))
        getRakeLogs.getRake(coachList)
        print("""







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
                TCMS Man Version 1.0 Raptor Distro 
              Author: Ben McGuffog, Support Engineer

        """)
        print('****** Logs gathered for: ' + ', '.join(coachList))
    else:
        print("""




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

        """)

    input("Press ENTER key to exit")


if __name__ == "__main__":
    main()
