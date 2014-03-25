Class Project for CS 3240 Spring 2014

Running on Ubuntu 12.04 LTS
Using Python 2.7

Install Watchdog and flask

```bash
pip install watchdog
pip install flask
```

Backup, then overwrite the inotify.py file that comes with Watchdog. 

```bash
cp /usr/local/lib/python2.7/dist-packages/watchdog/observers/inotify.py /usr/local/lib/python2.7/dist-packages/watchdog/observers/inotify.py.bak
cp <git repo>/inoitfy.py /usr/local/lib/python2.7/dist-packages/watchdog/observers/inotify.py
```

Create the server database.

```bash
sqlite3 server.db
```

Start the server by running ./server.py

Start the client by running ./client.py

You may need to change permissions to allow these files to be run.

```bash
chmod a+x server.py
chmod a+x client.py
```