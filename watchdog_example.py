import sys
import time
import logging
import os
import pwd
import requests
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler

server_url = "http://localhost:5000"

class OneDirHandler(FileSystemEventHandler):
    def on_created(self, event):
        print "Created " + event.src_path
    
    def on_deleted(self, event):
        print "Deleted " + event.src_path

    def on_modified(self, event):
        print "Modified " + event.src_path

    def on_moved(self, event):
        print "Moved " + event.src_path + " to " + event.dest_path

def get_username():
    return pwd.getpwuid(os.getuid()).pw_name

def start_service():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    username = get_username()
    directory = "/home/" + username + "/onedir/"

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
        password = raw_input("password: ")

        login_info = {'username': username, 'password': password}
        r = requests.post(server_url+"/login", data=login_info)
        if (r.text == "valid"):
            print "Valid Login!"
            start_service()
        else:
            print "Invalid login!"
    elif command.lower() == "sign up" or command.lower() == "signup":
        print "Sign up for OneDir!"

        username = raw_input("Enter a username: ")
        username_info = {"username": username}
        username_request = requests.post(server_url+"/check_username", data=username_info)

        while username_request.text == "invalid":
            username = raw_input("Username already exists. Enter another username: ")
            username_info = {"username": username}
            username_request = requests.post(server_url+"/check_username", data=username_info)
        password = raw_input("Enter a password: ")

        create_user_info = {'username': username, 'password': password}

        create_user_request = requests.post(server_url+"/create_user", data=create_user_info)

        start_service()
