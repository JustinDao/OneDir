#! /usr/bin/python

import sys
import time
import logging
import os
import pwd
import requests
import getpass
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler

server_url = "http://localhost:5000"

username = ""
password = ""

def get_username():
    return pwd.getpwuid(os.getuid()).pw_name

main_username = get_username()
directory = "/home/" + main_username + "/onedir/"

class OneDirHandler(FileSystemEventHandler):
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

        filepath = event.src_path.replace(directory, "")
        file_data = {'file': open(event.src_path, 'rb')}
        info = {'username': username, 'password': password, 'filepath': filepath}

        r = requests.put(server_url +"/modify_file", data=info, files=file_data)
        # print r.text

    def on_moved(self, event):
        print "Moved " + event.src_path + " to " + event.dest_path

        #handles file vs. dir on server
        
        src = event.src_path.replace(directory, "")
        dest = event.dest_path.replace(directory, "")

        info = {'username': username, 'password': password, 'src': src, 'dest': dest}

        r = requests.put(server_url +"/move_item", data=info)

        # print r.text


def start_service():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')    

    if not os.path.exists(directory):
        os.makedirs(directory)

    event_handler = OneDirHandler()
    # logging_handler = LoggingEventHandler()
    
    observer = Observer()
    # observer.schedule(logging_handler, directory, recursive=True)
    observer.schedule(event_handler, directory, recursive=True)

    observer.start()
    print "Service started."
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    print "Enter 'login' to login, or 'sign up' to create a new account:"

    valid_inputs = ["login", "signup", "sign up"]

    command = raw_input("")
    while(command.lower() not in valid_inputs):
        command = raw_input("")

    if command.lower() == "login":
        print "Login:"
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
