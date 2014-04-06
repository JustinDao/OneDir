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
from Queue import Queue
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler
from watchdog.events import FileCreatedEvent
from datetime import datetime
import sqlite3

server_url = "http://localhost:5000"

username = ""
password = ""

updated_at = str(datetime.now())

def get_username():
    return pwd.getpwuid(os.getuid()).pw_name

main_username = get_username()
directory = "/home/" + main_username + "/onedir/"

class OneDirHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global updated_at
        updated_at = str(datetime.now())

    def on_created(self, event):
        print "Created " + event.src_path

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
        print "Deleted " + event.src_path

        #handles file vs. dir on server

        filepath = event.src_path.replace(directory, "")
        info = {'username': username, 'password': password, 'filepath': filepath}
        r = requests.delete(server_url +"/delete_item", data=info)

        # print r.text


    def on_modified(self, event):
        print "Modified " + event.src_path

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
            print "Moved " + event.src_path + " to " + event.dest_path

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
        f = open(directory + filename, "w+")
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
    print sfiles, sfolders
    for i,f in enumerate(sfiles):
        sfiles[i] = f.replace(username + "/", "")

    for i,f in enumerate(sfolders):
        sfolders[i] = f.replace(username + "/", "")

    for i,f in enumerate(lfiles):
        lfiles[i] = f.replace("onedir/", "")

    for i,f in enumerate(lfolders):
        lfolders[i] = f.replace("onedir/", "")
    print sfiles, sfolders
    print ""
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
   

def folder_listener(handler, observer):
    while True:
        time.sleep(1)
        if not os.path.exists(directory):
            observer.stop()
            observer.join()
            restore_onedir_folder(username, password)
            observer = Observer()
            observer.schedule(handler, directory, recursive=True)
            observer.start()

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
    validlist = []
    for i in send_dict:
        if i != input:
            validlist.append(i)
    for i in validlist:
        del send_dict[i]
    a, sfiles, sfolders, spath = file_recurse(send_dict,sfiles, sfolders,"")
    print sfiles, sfolders
    for i,f in enumerate(sfiles):
        sfiles[i] = f.replace(username + "/", "")
    for i,f in enumerate(sfolders):
        sfolders[i] = f.replace(username + "/", "")
    print sfiles, sfolders
    filepath = input + "/"
    info = {'username': input2, 'dirpath': filepath}
    sfolders.remove(filepath)
    for f in sfolders:
        print f
        info = {'username': input2, 'dirpath': f}
        r = requests.post(server_url +"/create_dir2", data=info)

    for f in sfiles:
        directory12 = "/home/" + main_username + "/"
        file_data = {'file': open(directory12 + input2  + "/" + f, 'rb')}
        info = {'username': input2, 'filepath': f}
        r = requests.post(server_url +"/create_file2", data=info, files=file_data)

    for filename in sfiles:
        info1 = {'username': input2}
        r = requests.get(server_url +"/get_file2/" + filename, data=info1)
        f = open(directory + username  + "/" + filename, "w+")
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
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')    

    if not os.path.exists(directory):
        restore_onedir_folder(username, password)

    event_handler = OneDirHandler()
    # logging_handler = LoggingEventHandler()
    
    observer = Observer()
    # observer.schedule(logging_handler, directory, recursive=True)
    observer.schedule(event_handler, directory, recursive=True)

    observer.start()
    print "Service started."
    try:
        check_files()
        thread.start_new_thread ( folder_listener, (event_handler, observer) )
        while True:
            user_input = raw_input("Command: ")
            if user_input == "delete":
                deleteUser(username,password)
            if user_input == "share":
                share_files()

            # request_files()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def user_login():
    print "Login:"
    global username
    global password
    username = raw_input("username: ")
    username_info = {"username": username}
    username_request = requests.post(server_url+"/check_username", data=username_info)


    while username_request.text != "exists":
        username = raw_input("Username does not exist. Re-enter username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)

    password = getpass.getpass("password: ")

    login_info = {'username': username, 'password': password}
    r = requests.post(server_url+"/login", data=login_info)

    while (r.text != "valid"):
        print "Bad password."
        password = getpass.getpass("Retype password: ")
        login_info = {'username': username, 'password': password}
        r = requests.post(server_url+"/login", data=login_info)

    start_service()

def admin_login(username, password):
    print "Login:"
    username = raw_input("username: ")
    username_info = {"username": username}

    username_request = requests.post(server_url+"/check_admin", data=username_info)

    while username_request.text != "exists":
        username = raw_input("Admin does not exist. Re-enter admin name: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_admin", data=username_info)

    password = getpass.getpass("password: ")

    login_info = {'username': username, 'password': password}
    r = requests.post(server_url+"/admin_login", data=login_info)

    while (r.text != "valid"):
        print "Bad password."
        password = getpass.getpass("Retype password: ")
        login_info = {'username': username, 'password': password}
        r = requests.post(server_url+"/admin_login", data=login_info)

    print "Logged in as Admin!"

def deleteFiles_admin():
    print "Delete a file:"
    username = raw_input("username: ")
    username_info = {"username": username}
    username_request = requests.post(server_url+"/check_username", data=username_info)

    while username_request.text != "exists":
        username = raw_input("Username does not exist. Re-enter username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)
    password = getpass.getpass("password: ")

    delete_info = {'username': username, 'password': password}
    r = requests.post(server_url+"/login", data=delete_info)
    #q = requests.post(server_url+"/delete_user", data=delete_info)

    while r.text != "valid":
        print "Bad password."
        password = getpass.getpass("Retype password: ")
        delete_info = {'username': username, 'password': password}
        r = requests.post(server_url+"/login", data=delete_info)
        #q = requests.post(server_url+"/delete_user", data=delete_info)
    info = {'username': username, 'password': password}
    r = requests.get(server_url +"/request_files", data=info)
    server_files =  r.json()
    server_files = unicode_dict_to_string(server_files)
    sfiles = []
    sfolders = []
    flist, sfiles, sfolders, path = file_recurse(server_files, sfiles, sfolders, "")

    for i,f in enumerate(sfiles):
        sfiles[i] = f.replace(username + "/", "")

    for i,f in enumerate(sfolders):
        sfolders[i] = f.replace(username + "/", "")

    print sfolders, sfiles
    file_delete = raw_input("which folder or file do you want to delete from the list above: ")
    if file_delete in sfiles and file_delete in sfolders:
        print "Asdf"

    for f in sfiles:
        # if file on server not on local, remove from server
        info = {'username': username, 'password': password, 'filepath': f}
        #r = requests.delete(server_url +"/delete_item", data=info)

    for f in sfolders:
        # if folder on server not on local, remove from server
        info = {'username': username, 'password': password, 'filepath': f}
        #r = requests.delete(server_url +"/delete_item", data=info)
    #q = requests.post(server_url+"/delete_user", data=delete_info)
    print "deleted"

def deleteUser(username, password):
    print "Delete a account:"
    username = raw_input("username: ")
    username_info = {"username": username}
    username_request = requests.post(server_url+"/check_username", data=username_info)

    while username_request.text != "exists":
        username = raw_input("Username does not exist. Re-enter username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)
    password = getpass.getpass("password: ")

    delete_info = {'username': username, 'password': password}
    r = requests.post(server_url+"/login", data=delete_info)
    #q = requests.post(server_url+"/delete_user", data=delete_info)

    while r.text != "valid":
        print "Bad password."
        password = getpass.getpass("Retype password: ")
        delete_info = {'username': username, 'password': password}
        r = requests.post(server_url+"/login", data=delete_info)
        #q = requests.post(server_url+"/delete_user", data=delete_info)
    info = {'username': username, 'password': password}
    r = requests.get(server_url +"/request_files", data=info)
    server_files =  r.json()
    server_files = unicode_dict_to_string(server_files)
    sfiles = []
    sfolders = []
    path = directory
    flist, sfiles, sfolders, path = file_recurse(server_files, sfiles, sfolders, "")
    for i,f in enumerate(sfiles):
        sfiles[i] = f.replace(username + "/", "")

    for i,f in enumerate(sfolders):
        sfolders[i] = f.replace(username + "/", "")
    for f in sfiles:
        # if file on server not on local, remove from server
        info = {'username': username, 'password': password, 'filepath': f}
        r = requests.delete(server_url +"/delete_item", data=info)

    for f in sfolders:
        # if folder on server not on local, remove from server
        info = {'username': username, 'password': password, 'filepath': f}
        r = requests.delete(server_url +"/delete_item", data=info)
    q = requests.post(server_url+"/delete_user", data=delete_info)
    print "deleted"

if __name__ == "__main__":
    print "Enter 'login' to login, or 'sign up' to create a new account, or 'delete' to delete your account"

    valid_inputs = ["login", "signup", "sign up", "admin login","delete"]


    command = raw_input("")
    while(command.lower() not in valid_inputs):
        command = raw_input("")

    if command.lower() == "login":
        user_login()

    elif command.lower() == "admin login":
        admin_login(username, password)
        print "Enter 'delete' to delete a user"

        valid_inputs_admin = ["delete"]

        input_admin = raw_input("")
        while (input_admin.lower() not in valid_inputs_admin):
            input_admin = raw_input("")

        if input_admin.lower() == "delete":
            deleteUser(username,password)

    elif command.lower() == "delete":
        deleteUser(username,password)

        info = {'username': username, 'password': password}
        r = requests.get(server_url +"/request_files", data=info)

    elif command.lower() == "sign up" or command.lower() == "signup":
        print "Sign up for OneDir!"

        username = raw_input("Enter a username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)

        while username_request.text == "exists":
            username = raw_input("Username already exists. Enter another username: ")
            username_info = {"username": username}
            username_request = requests.post(server_url+"/check_username", data=username_info)
        password = getpass.getpass("Enter a password: ")
        password_confirmation = getpass.getpass("Confirm your password: ")

        while (password != password_confirmation):
            print "Passwords did not match."
            password = getpass.getpass("Re-enter your password: ")
            password_confirmation = getpass.getpass("Confirm your password: ")

        create_user_info = {'username': username, 'password': password}

        create_user_request = requests.post(server_url+"/create_user", data=create_user_info)

        start_service()

    elif command.lower() == "get":
        conn = sqlite3.connect('server.db')
        result = []
        with conn:
            cur = conn.cursor()
            sql_cmd = "select * from users"
            cur.execute(sql_cmd)
            while True:
                page_row = cur.fetchone()
                if page_row is None:
                    break
                else:
                    print page_row

    elif command.lower() == "change":
        username = raw_input("Enter a username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)
        if username_request.text == "exists":
            old_password = getpass.getpass("current password: ")
            login_info = {'username': username, 'password': old_password}
            r = requests.post(server_url+"/login", data=login_info)
            while (r.text != "valid"):
                print "Bad password."
                old_password = getpass.getpass("current password: ")
                login_info = {'username': username, 'password': old_password}
                r = requests.post(server_url+"/login", data=login_info)
            new_password = getpass.getpass("New password: ")
            password_confirmation = getpass.getpass("Confirm your password: ")
            while (new_password != password_confirmation):
                print "Passwords did not match."
                new_password = getpass.getpass("Re-enter your password: ")
                password_confirmation = getpass.getpass("Confirm your password: ")
        conn = sqlite3.connect('server.db')
        result = []
        with conn:
            cur = conn.cursor()
            sql_cmd = "update users set password=? where username=?"
            cur.execute(sql_cmd, (new_password, username))
