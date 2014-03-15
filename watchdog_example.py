import sys
import time
import logging
import os
import pwd
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler

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
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()