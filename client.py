#! /usr/bin/python

import sys
import time
import logging
import os
import pwd
import requests
import getpass
import collections
import thread
import re
import shutil
import hashlib
from Queue import Queue
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler
from watchdog.events import FileCreatedEvent
from datetime import datetime
import sqlite3

class OneDirObserver(Observer):
    def __init__(self, *args):
        self.listening = True
        super(OneDirObserver, self).__init__(*args)

    def start_listening(self):
        self.listening = True

    def stop_listening(self):
        self.listening = False

    def dispatch_events(self, event_queue, timeout):
        if self.listening:
            super(OneDirObserver, self).dispatch_events(event_queue, timeout)
        else:
            # eats up event to ignore it
            event, watch = event_queue.get(block=True, timeout=timeout)


requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

server_url = "http://localhost:5000"

username = ""
password = ""
logged_in = False

updated_at = str(datetime.now())

observer = OneDirObserver()

def get_username():
    return pwd.getpwuid(os.getuid()).pw_name

main_username = get_username()
directory = "/home/" + main_username + "/onedir/"

class OneDirHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global updated_at
        updated_at = str(datetime.now())

    def on_created(self, event):
        # print "Created " + event.src_path

        if os.path.isfile(event.src_path):
            filepath = event.src_path.replace(directory, "")
            file_data = {'file': open(event.src_path, 'rb')}
            info = {'username': username, 'password': password, 'filepath': filepath}

            r = requests.post(server_url +"/create_file", data=info, files=file_data)

        elif os.path.isdir(event.src_path):
            dirpath = event.src_path.replace(directory, "")
            info = {'username': username, 'password': password, 'dirpath': dirpath}

            r = requests.post(server_url +"/create_dir", data=info)
        # print r.text
        
    
    def on_deleted(self, event):
        # print "Deleted " + event.src_path

        #handles file vs. dir on server

        filepath = event.src_path.replace(directory, "")
        info = {'username': username, 'password': password, 'filepath': filepath}
        r = requests.delete(server_url +"/delete_item", data=info)

        # print r.text


    def on_modified(self, event):
        # print "Modified " + event.src_path

        #Should never encounter this with a directory
        #but weird stuff happens when moved outside watchdog directory

        filepath = event.src_path.replace(directory, "")
        try:
            file_data = {'file': open(event.src_path, 'rb')}
        except: 
            # should only hit this when directories are moved outside watched directory, and then deleted.
            return
        info = {'username': username, 'password': password, 'filepath': filepath}

        r = requests.put(server_url +"/modify_file", data=info, files=file_data)
        # print r.text

    def on_moved(self, event):
        if event.src_path is not None:
            # print "Moved " + event.src_path + " to " + event.dest_path

            #handles file vs. dir on server
            
            src = event.src_path.replace(directory, "")
            dest = event.dest_path.replace(directory, "")

            info = {'username': username, 'password': password, 'src': src, 'dest': dest}

            r = requests.put(server_url +"/move_item", data=info)

            # print r.text
        else:
            new_event = FileCreatedEvent(event.dest_path)
            self.on_created(new_event)

def unicode_dict_to_string(data):
    '''
    http://stackoverflow.com/questions/1254454/
    '''
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(unicode_dict_to_string, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(unicode_dict_to_string, data))
    else:
        return data

def get_local_file_list(path):
    """
    http://code.activestate.com/recipes/577879-create-a-nested-dictionary-from-oswalk/
    Creates a nested dictionary that represents the folder structure of rootdir
    """

    dir = {}
    rootdir = path.rstrip(os.sep)
    start = rootdir.rfind(os.sep) + 1
    for path, dirs, files in os.walk(rootdir):
        folders = path[start:].split(os.sep)
        subdir = dict.fromkeys(files)
        parent = reduce(dict.get, folders[:-1], dir)
        parent[folders[-1]] = subdir
    return dir


def file_recurse(dict, files, folders, path):
    if dict is not None:
        for key in dict:
            if dict[key] is None:
                files.append(path + key)
            else:
                folders.append(path + key + "/")
                file_recurse(dict[key], files, folders, path + key + "/")

    return dict, files, folders, path


def get_server_files_and_folders():
    info = {'username': username, 'password': password}
    r = requests.get(server_url +"/request_files", data=info)
    server_files =  r.json()
    server_files = unicode_dict_to_string(server_files)

    local_directory = get_local_file_list(directory)

    folders = []
    files = []    

    path = directory
    if local_directory['onedir'] != server_files[username]:
        flist, files, folders, path = file_recurse(server_files[username], files, folders, "")
    return files, folders

def restore_onedir_folder(username, password):
    os.makedirs(directory)
    info = {'username': username, 'password': password}

    files, folders = get_server_files_and_folders()

    for folder in folders:
        if not os.path.exists(directory + folder):
            os.makedirs(directory + folder)

    for filename in files:
        r = requests.get(server_url +"/get_file/" + filename, data=info)

        with open(directory + filename, "w+") as f:
            f.write(r.content)


def check_files():
    #local folder gets copied to server

    info = {'username': username, 'password': password}
    r = requests.get(server_url +"/request_files", data=info)
    server_files =  r.json()

    server_files = unicode_dict_to_string(server_files)
    local_files = get_local_file_list(directory)

    sfiles = []
    sfolders = []
    lfiles = []
    lfolders = []

    s, sfiles, sfolders, spath = file_recurse(server_files, sfiles, sfolders, "")
    l, lfiles, lfolders, lpath = file_recurse(local_files, lfiles, lfolders, "")
    for i,f in enumerate(sfiles):
        sfiles[i] = f.replace(username + "/", "")

    for i,f in enumerate(sfolders):
        sfolders[i] = f.replace(username + "/", "")

    for i,f in enumerate(lfiles):
        lfiles[i] = f.replace("onedir/", "")

    for i,f in enumerate(lfolders):
        lfolders[i] = f.replace("onedir/", "")
    for f in sfiles:
        if f not in lfiles:
            # if file on server not on local, remove from server
            info = {'username': username, 'password': password, 'filepath': f}
            r = requests.delete(server_url +"/delete_item", data=info)

    for f in sfolders:
        if f not in lfolders:
            # if folder on server not on local, remove from server
            info = {'username': username, 'password': password, 'filepath': f}
            r = requests.delete(server_url +"/delete_item", data=info)

    for f in lfolders:
        if f not in sfolders:
            # if folder on local not on server, create in server
            info = {'username': username, 'password': password, 'dirpath': f}
            r = requests.post(server_url +"/create_dir", data=info)

    for f in lfiles:
        if f not in sfiles:
            # if file on local not on server, create in server
            file_data = {'file': open(directory + f, 'rb')}
            info = {'username': username, 'password': password, 'filepath': f}
            r = requests.post(server_url +"/create_file", data=info, files=file_data)
        else:
            # if file is on client and on server, update the server file
            # TODO: Check if file is different first before uploading
            file_data = {'file': open(directory + f, 'rb')}
            info = {'username': username, 'password': password, 'filepath': f}
            r = requests.post(server_url +"/create_file", data=info, files=file_data)

def folder_listener(handler):
    global username
    global password
    global logged_in
    global observer
    while True:
        time.sleep(1)
        if not logged_in:
            break
        if not os.path.exists(directory):
            observer.stop()
            observer.join()
            restore_onedir_folder(username, password)
            observer = OneDirObserver()
            observer.schedule(handler, directory, recursive=True)
            observer.start()
        else:
            if observer.listening:
                request_files()

def request_files():
    global username
    global password
    global observer
    observer.stop_listening()
    info = {'username': username, 'password': password}
    r = requests.get(server_url +"/request_files", data=info)
    server_files =  r.json()

    server_files = unicode_dict_to_string(server_files)
    local_files = get_local_file_list(directory)

    sfiles = []
    sfolders = []
    lfiles = []
    lfolders = []

    s, sfiles, sfolders, spath = file_recurse(server_files, sfiles, sfolders, "")
    l, lfiles, lfolders, lpath = file_recurse(local_files, lfiles, lfolders, "")
    for i,f in enumerate(sfiles):
        sfiles[i] = f.replace(username + "/", "")

    for i,f in enumerate(sfolders):
        sfolders[i] = f.replace(username + "/", "")

    for i,f in enumerate(lfiles):
        lfiles[i] = f.replace("onedir/", "")

    for i,f in enumerate(lfolders):
        lfolders[i] = f.replace("onedir/", "")

    # compare local files to its mirror on the server
    for f in lfiles:
        file_data = {'file': open(directory + f, 'rb')}
        info = {'username': username, 'password': password, 'filepath': f}
        r = requests.post(server_url +"/check_file", data=info, files=file_data)
        if r.text == "False":
            
            data = requests.get(server_url +"/get_file/" + f, data=info)
            with open(directory + f, "w+") as fi:
                fi.write(data.content)

    for f in sfolders:
        if f not in lfolders:
            # if folder on server not on local, add to local
            os.makedirs(directory + f)

    for f in sfiles:
        if f not in lfiles:
            # if file on server not on local, add to local
            info = {'username': username, 'password': password, 'filepath': f}
            r = requests.get(server_url +"/get_file/" + f, data=info)

            with open(directory + f, "w+") as fi:
              fi.write(r.content) 

    l, lfiles, lfolders, lpath = file_recurse(local_files, lfiles, lfolders, "")
    for i,f in enumerate(lfiles):
        lfiles[i] = f.replace("onedir/", "")

    for i,f in enumerate(lfolders):
        lfolders[i] = f.replace("onedir/", "")

    for f in lfolders:
        if f not in sfolders:
            # if folder still on local after getting server files, remove it
            # fixes folder renames
            try:
                shutil.rmtree(directory + f)
            except OSError:
                pass

    for f in lfiles:
        if f not in sfiles:
            # if file was renamed remove old local file. 
            try:
                os.remove(directory + f)
            except OSError:
                pass

    observer.start_listening()

    # #TODO RENAMING FOLDERS ON SERVER
    # #TODO: Check for updated files on server


def user_command(user_input):
    global username
    global password
    global logged_in
    global observer
    if user_input == "logout":
        username = ""
        password = ""
        logged_in = False
        print "You have been logged out."
        main_program()
    elif user_input == "delete":
        deleteAccount()
        main_program()
    elif user_input == "share":
        share_files()
    elif user_input == "history":
        get_history()
    elif user_input.split(" ")[0] == "history":
        store_history(user_input.split(" ")[1])
    elif user_input == "change password":
        change_password()
    elif user_input == "pause":
        observer.stop_listening()
        info = {'username': username, 'password': password}
        requests.post(server_url + "/log_stop", data=info)
        print "Synchronzation Off"
    elif user_input == "unpause":
        observer.start_listening()
        info = {'username': username, 'password': password}
        requests.post(server_url + "/log_start", data=info)
        print "Synchronzation On"
    else:
        print user_input + " is not a command."

def change_password():
    global username
    global password
    new_password = getpass.getpass("Enter a new password: ")
    new_password_confirmation = getpass.getpass("Confirm your new password: ")

    while (new_password != new_password_confirmation):
        print "Passwords did not match."
        new_password = getpass.getpass("Re-enter your new password: ")
        new_password_confirmation = getpass.getpass("Confirm your new password: ")

    update_user_info = {'username': username, 'old_password': password, 'new_password': new_password}
    update_user_request = requests.post(server_url+"/update_password", data=update_user_info)

    if update_user_request.text == "Password Updated":
        password = new_password
    else:
        print "failed"

def get_history():
    global username
    global password
    login_info = {'username': username, 'password': password}
    r = requests.get(server_url + "/get_history", data=login_info)
    print r.text

def store_history(filename):
    global username
    global password
    with open(directory + filename, "w") as f:
        login_info = {'username': username, 'password': password}
        r = requests.get(server_url + "/get_history", data=login_info)
        f.write(r.text)

def find_path(list,folder_path):
    for i in list:
        if i == '/':
            folder_path += '/'
            return folder_path
        else:
            folder_path += i

def share_files():
    files = get_local_file_list(directory)
    print files
    keyList = {}
    while(True):
        input = raw_input("Enter a folder or file that you want to send: ")
        if input in file_List(files,keyList):
            send_dict = file_List(files,keyList)[input]
            break
        print "it does not exist. Please enter valid folder or file."
    while(True):
        input2 = raw_input("To: ")
        if input2 != username:
            username_info = {"username": input2}
            username_request = requests.post(server_url+"/check_username", data=username_info)
            while username_request.text != "exists":
                input2 = raw_input("Username does not exist. Re-enter username: ")
                username_info = {"username": input2}
                username_request = requests.post(server_url+"/check_username", data=username_info)
            break
        print "you cannot send it to yourself. Re-enter username."

    sfiles = []
    sfolders = []
    rfiles = []
    rfolders = []
    validlist = []
    rpath = ""
    spath = ""
    if send_dict[input] != None:
        for i in send_dict:
            if i != input:
                validlist.append(i)
        for i in validlist:
            del send_dict[i]
        a, sfiles, sfolders, spath = file_recurse(send_dict,sfiles, sfolders,spath)
        for f in sfolders:
            info = {'username': input2, 'dirpath': f}
            r = requests.post(server_url +"/create_dir2", data=info)

        for f in sfiles:
            directory1 = "/home/" + main_username + "/onedir/"
            file_data = {'file': open(directory1 + f, 'rb')}
            info = {'username': input2, 'filepath': f}
            r = requests.post(server_url +"/create_file2", data=info, files=file_data)

        for filename in sfiles:
            info1 = {'username': input2}
            directory1 = "/home/" + main_username + "/onedir/"
            r = requests.get(server_url +"/get_file2/" + filename, data=info1)
            f = open(directory1 + filename, "w+")
            f.write(r.content)
    else:
        a, rfiles, rfolders, rpath = file_recurse(files,rfiles, rfolders,rpath)
        newFiles = []
        for i in rfiles:
            s = list(i)
            aa = s.__len__()-4
            if i[aa:] == input:
                newFiles.append(i)
        for i,f in enumerate(newFiles):
            newFiles[i] = f.replace("onedir/","")
        zz = list(newFiles[0])
        folder_path = ""
        path2 = []
        while(True):
            qq = find_path(zz,folder_path)
            qwer= list(input)
            if zz == qwer:
                path2.append(input+'/')
                break
            path2.append(qq)
            ww = list(qq)
            for i in ww:
                zz.remove(i)
        path3 = []
        tfile = []
        temp = ""
        for i in path2:
            temp += i
            path3.append(temp)
        tfile.append(path3[path3.__len__()-1])
        path3.remove(path3[path3.__len__()-1])

        for f in path3:
            f = f[:-1]
            info = {'username': input2, 'dirpath': f}
            r = requests.post(server_url +"/create_dir2", data=info)

        for f in tfile:
            f = f[:-1]
            directory1 = "/home/" + main_username + "/onedir/"
            file_data = {'file': open(directory1 + f, 'rb')}
            info = {'username': input2, 'filepath': f}
            r = requests.post(server_url +"/create_file2", data=info, files=file_data)

        for filename in tfile:
            filename = filename[:-1]
            info1 = {'username': input2}
            directory1 = "/home/" + main_username + "/onedir/"
            r = requests.get(server_url +"/get_file2/" + filename, data=info1)
            f = open(directory1 + filename, "w+")
            f.write(r.content)

def file_List(dict,keyList):
    if dict is not None:
        for key in dict:
            if dict[key] is None:
                keyList[key] = dict
            else:
                keyList[key] = dict
                file_List(dict[key], keyList)
    return keyList

def start_service():
    global logged_in
    global observer
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    if not os.path.exists(directory):
        restore_onedir_folder(username, password)

    event_handler = OneDirHandler()
    # logging_handler = LoggingEventHandler()
    # observer.schedule(logging_handler, directory, recursive=True)
    observer = OneDirObserver()
    observer.schedule(event_handler, directory, recursive=True)

    observer.start()
    logged_in = True
    print "Service started."
    try:
        check_files()
        thread.start_new_thread ( folder_listener, (event_handler,) )
        while True:
            user_input = raw_input("Command: ")
            user_command(user_input)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def user_login():
    print "Login:"
    global username
    global password
    global logged_in
    username = raw_input("username: ")
    username_info = {"username": username}
    username_request = requests.post(server_url+"/check_username", data=username_info)

    while username_request.text != "exists":
        username = raw_input("Username does not exist. Re-enter username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)

    password_before_hash = getpass.getpass("password: ")
    password = hashlib.md5(password_before_hash).hexdigest()

    login_info = {'username': username, 'password': password}
    r = requests.post(server_url+"/login", data=login_info)

    while (r.text != "valid"):
        print "Bad password."

        password_before_hash = getpass.getpass("Retype password: ")
        password = hashlib.md5(password_before_hash).hexdigest()

        login_info = {'username': username, 'password': password}
        r = requests.post(server_url+"/login", data=login_info)

    start_service()

def admin_login():
    global username
    global password
    print "Login:"
    username = raw_input("Admin username: ")
    username_info = {"username": username}

    username_request = requests.post(server_url+"/check_admin", data=username_info)

    while username_request.text != "exists":
        username = raw_input("Admin does not exist. Re-enter admin name: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_admin", data=username_info)

    password_before_hash = getpass.getpass("Admin password: ")
    password = hashlib.md5(password_before_hash).hexdigest()

    login_info = {'username': username, 'password': password}
    r = requests.post(server_url+"/admin_login", data=login_info)

    while (r.text != "valid"):
        print "Bad password."

        password_before_hash = getpass.getpass("Retype password: ")
        password = hashlib.md5(password_before_hash).hexdigest()

        login_info = {'username': username, 'password': password}
        r = requests.post(server_url+"/admin_login", data=login_info)

    start_admin()

def start_admin():
    while True:
        admin_input = raw_input("Admin Command: ")
        admin_command(admin_input)


def admin_command(admin_input):
    global username
    global password
    if admin_input.lower() == "get":
        admin_info = {'username': username, 'password' : password}
        r = requests.post(server_url + "/get_user_data", data=admin_info)
        a = unicode_dict_to_string(r.json())
        print a["info"]

    elif admin_input.lower() == "change":
        admin_change_password()
    elif admin_input.lower() == "remove user":
        admin_remove_user()
    elif admin_input.lower() == "user files":
        admin_user_files()
    elif admin_input.lower() == "history":
        admin_history()
    elif admin_input.lower() == "logout":
        username = ""
        password = ""
        logged_in = False
        print "You have been logged out."
        main_program()

def admin_history():
    global username
    global password

    uname = raw_input("Enter a username: ")    

    uname_info = {"username": uname}
    uname_request = requests.post(server_url+"/check_username", data=uname_info)

    if uname_request.text == "exists":
        info = {'admin_name': username, 'admin_pw': password, 'username': uname}
        r = requests.get(server_url + "/get_user_history", data=info)
        print r.text
    else:
        print "User does not exist"


def admin_user_files():
    global username
    global password
    uname = raw_input("Enter a username: ")    

    uname_info = {"username": uname}
    uname_request = requests.post(server_url+"/check_username", data=uname_info)

    if uname_request.text == "exists":
        info = {"admin_name": username, "admin_pw": password, "username": uname}
        r = requests.get(server_url + "/user_file_info", data=info)

        files = r.json()
        files = unicode_dict_to_string(files)

        num_files = files["number_of_files"]

        del files["number_of_files"]

        print "Number of Files: " + str(num_files)

        print

        for f in files:
            print f + " " + files[f]
    else:
        print "User does not exist"

    

def admin_remove_user():
    global username
    global password
    global logged_in

    uname = raw_input("Enter a username: ")
    uname_info = {"username": uname}
    uname_request = requests.post(server_url+"/check_username", data=uname_info)

    if uname_request.text == "exists":

        confirm = raw_input("Are you sure you want to delete your account? (yes/no): ")
        print "This will delete all of your files and information from the database."
        confirm2 = raw_input("ARE YOU ABSOLUTELY SURE? (yes/no): ")

        if confirm == "yes" and confirm2 == "yes":
            login_info = {'admin_name': username, 'admin_pw': password, 'username': uname}
            r = requests.delete(server_url+"/admin_delete_user", data=login_info)

    else:
        print "User does not exist"

def admin_change_password():
    global username
    global password
    uname = raw_input("Enter a username: ")
    uname_info = {"username": uname}
    uname_request = requests.post(server_url+"/check_username", data=uname_info)

    if uname_request.text == "exists":
        new_password = getpass.getpass("User's new password: ")
        password_confirmation = getpass.getpass("Confirm new password: ")
        while (new_password != password_confirmation):
            print "Passwords did not match."
            new_password = getpass.getpass("Re-enter new password: ")
            password_confirmation = getpass.getpass("Confirm new password: ")

        update_user_info = {'admin_name': username, 'admin_pw': password, 'username': uname, 'new_password': new_password}
        update_user_request = requests.post(server_url+"/admin_update_password", data=update_user_info)

    else:
        print "User does not exist"

def deleteAccount():
    global username
    global password
    global logged_in
    confirm = raw_input("Are you sure you want to delete your account? (yes/no): ")
    print "This will delete all of your files and information from the database."
    confirm2 = raw_input("ARE YOU ABSOLUTELY SURE? (yes/no): ")

    if confirm == "yes" and confirm2 == "yes":
        login_info = {'username': username, 'password': password}
        r = requests.delete(server_url+"/delete_user", data=login_info)
        username = ""
        password = ""
        logged_in = False
        

def main_program():
    global username
    global password
    print "Enter 'login' to login, or 'sign up' to create a new account"

    valid_inputs = ["login", "signup", "sign up", "admin login"]


    command = raw_input("")
    while(command.lower() not in valid_inputs):
        command = raw_input("")

    if command.lower() == "login":
        user_login()

    elif command.lower() == "admin login":
        admin_login()

    elif command.lower() == "sign up" or command.lower() == "signup":
        print "Sign up for OneDir!"

        username = raw_input("Enter a username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)

        while username_request.text == "exists" or not re.match("^[A-Za-z0-9_-]*$", username):
            if not re.match("^[A-Za-z0-9]*$", username):
                username = raw_input("Not a valid username. Enter another username: ")
            else:
                username = raw_input("Username already exists. Enter another username: ")
            username_info = {"username": username}
            username_request = requests.post(server_url+"/check_username", data=username_info)
        password_before_hash = getpass.getpass("Enter a password: ")
        password_confirmation = getpass.getpass("Confirm your password: ")

        while (password_before_hash != password_confirmation):
            print "Passwords did not match."
            password_before_hash = getpass.getpass("Re-enter your password: ")
            password_confirmation = getpass.getpass("Confirm your password: ")

        password = hashlib.md5(password_before_hash).hexdigest()

        create_user_info = {'username': username, 'password': password}

        create_user_request = requests.post(server_url+"/create_user", data=create_user_info)

        start_service()

if __name__ == "__main__":
    try:
        main_program()
    except requests.exceptions.ConnectionError:
        print "Not connected to server."

