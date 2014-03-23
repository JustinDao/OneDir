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

if __name__ == "__main__":
    print "Login:"
    username = raw_input("username: ")
    password = raw_input("password: ")

    login_info = {'username': username, 'password': password}
    r = requests.post(server_url+"/login", data=login_info)
    if (r.text == "Valid!"):
        print "Valid Login!"
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

        username = get_username()
        directory = "/home/" + username + "/onedir/"

        if not os.path.exists(directory):
            os.makedirs(directory)

        event_handler = OneDirHandler()
        logging_handler = LoggingEventHandler()
        
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
    else:
        print "Invalid login!"