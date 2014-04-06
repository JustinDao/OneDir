from app import app
from flask import request
from flask import json
from flask import make_response
from flask import send_from_directory
import sqlite3
import os
import shutil
import datetime



@app.route('/')
@app.route('/index')
def index():
  return "Hello, World!"

@app.route('/login', methods=['POST'])
def login():
  if valid_login(request.form['username'], request.form['password']):
    return "valid"
  else:
    return "invalid"



@app.route('/admin_login', methods=['POST'])
def admin_login():
  if valid_admin_login(request.form['username'], request.form['password']):
    return "valid"
  else:
    return "invalid"


@app.route('/check_username', methods=['POST'])
def check_username_request():
  if user_exists(request.form['username']):
    return "exists"
  else:
    return "does not exist"

@app.route('/check_admin', methods=['POST'])
def check_admin_request():
  if admin_exists(request.form['username']):
    return "exists"
  else:
    return "does not exist"

@app.route('/create_user', methods=['POST'])
def create_user_request():
  create_user(request.form['username'], request.form['password'])
  return "User created"

@app.route('/create_file', methods=['POST'])
def create_file_request():
  username = request.form['username']
  if valid_login(username, request.form['password']):
    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      os.makedirs(main_path)

    filepath = main_path + request.form['filepath']
    f = request.files['file']
    f.save(filepath)

    log(username, "Created File", filepath)

    return "File created"
  return "Failed to create file."

@app.route('/create_file2', methods=['POST'])
def create_file_request2():
  username = request.form['username']
  if user_exists(username):
    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      os.makedirs(main_path)

    filepath = main_path + request.form['filepath']
    f = request.files['file']
    f.save(filepath)

    return "File created"
  return "Failed to create file."

@app.route('/modify_file', methods=['PUT'])
def modify_file_request():
  username = request.form['username']
  if valid_login(username, request.form['password']):
    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      return "File does not exist."

    filepath = main_path + request.form['filepath']
    
    if os.path.isfile(filepath):
      f = request.files['file']
      f.save(filepath)
      log(username, "Modified File", filepath)
      return "File modified"
    else:
      return "File does not exist."
  return "Failed to modify file."




@app.route('/move_item', methods=['PUT'])
def move_item_request():
  username = request.form['username']
  if valid_login(username, request.form['password']):
    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      return "File does not exist."

    src = main_path + request.form['src']
    dest = main_path + request.form['dest']

    if os.path.isfile(src) or os.path.isdir(src):
      os.rename(src, dest)

    if os.path.isfile(dest):
      log(username, "Moved File", src, dest)
      return "File moved."
    elif os.path.isdir(dest):
      log(username, "Moved Directory", src, dest)
      return "Directory moved."
  return "Failed to move item."


@app.route('/delete_item', methods=['DELETE'])
def delete_item_request():
  username = request.form['username']
  if valid_login(username, request.form['password']):
    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      return "File does not exist."

    filepath = main_path + request.form['filepath']

    if os.path.isfile(filepath):
      os.remove(filepath)
      log(username, "Deleted File", filepath)
      return "File deleted."
    elif os.path.isdir(filepath):
      shutil.rmtree(filepath)
      log(username, "Deleted Directory", filepath)
      return "Directory deleted."    
  return "Failed to delete item."






@app.route('/create_dir', methods=['POST'])
def create_dir_request():
  username = request.form['username']
  if valid_login(username, request.form['password']):
    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      os.makedirs(main_path)

    dirpath = main_path + request.form['dirpath']

    if not os.path.exists(dirpath):
      os.makedirs(dirpath)
      log(username, "Created Directory", dirpath)
      return "Directory created"
    return "Directory already exists"

  return "Failed to create directory."


@app.route('/create_dir2', methods=['POST'])
def create_dir_request2():
  username = request.form['username']
  if user_exists(username):
    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      os.makedirs(main_path)

    dirpath = main_path + request.form['dirpath']

    if not os.path.exists(dirpath):
      os.makedirs(dirpath)
      return "Directory created"
    return "Directory already exists"

  return "Failed to create directory."


@app.route('/request_files', methods=['GET'])
def request_files():
  username = request.form['username']
  if valid_login(username, request.form['password']):
    """
    http://code.activestate.com/recipes/577879-create-a-nested-dictionary-from-oswalk/
    Creates a nested dictionary that represents the folder structure of rootdir
    """

    dir = {}

    cwd = os.getcwd()
    main_path = cwd + "/" + username + "/"

    if not os.path.exists(main_path):
      os.makedirs(main_path)

    rootdir = main_path.rstrip(os.sep)
    start = rootdir.rfind(os.sep) + 1
    for path, dirs, files in os.walk(rootdir):
        folders = path[start:].split(os.sep)
        subdir = dict.fromkeys(files)
        parent = reduce(dict.get, folders[:-1], dir)
        parent[folders[-1]] = subdir
    return json.jsonify(**dir)

@app.route('/get_file/<path:filename>', methods=['GET'])
def get_file(filename):
  username = request.form['username']

  if valid_login(username, request.form['password']):

    cwd = os.getcwd()
    main_path = cwd + "/" + username

    if os.path.isfile(main_path + "/" + filename): 
      return send_from_directory(main_path, filename)

  return "Failed"

@app.route('/delete_user', methods=['DELETE'])
def delete_user_request():
  username = request.form['username']
  print "delete request"
  if valid_login(username, request.form['password']):

    cwd = os.getcwd()
    main_path = cwd + "/" + username

    shutil.rmtree(main_path)

    remove_user_from_database(username, request.form['password'])
    print "Deleted"

  return "Failed"


@app.route('/get_file2/<path:filename>', methods=['GET'])
def get_file2(filename):
  username = request.form['username']
  if user_exists(username):

    cwd = os.getcwd()
    main_path = cwd + "/" + username

    if os.path.isfile(main_path + "/" + filename):
      return send_from_directory(main_path, filename)

  return "Failed"

def valid_login(username, password):
  connection = sqlite3.connect('server.db')
  cursor = connection.cursor()

  info = (username, password)
  cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", info)

  user = cursor.fetchall()

  connection.commit()
  connection.close()

  if user:
    return True
  else:
    return False

def valid_admin_login(username, password):
  connection = sqlite3.connect('server.db')
  cursor = connection.cursor()

  info = (username, password)
  cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", info)

  user = cursor.fetchall()

  connection.commit()
  connection.close()

  if user:
    return True
  else:
    return False

def user_exists(username):
  connection = sqlite3.connect('server.db')
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM users WHERE username = ?", (username,) )

  user = cursor.fetchall()

  connection.commit()
  connection.close()

  if user:
    return True
  else:
    return False


def admin_exists(username):
  connection = sqlite3.connect('server.db')
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM admins WHERE username = ?", (username,) )

  user = cursor.fetchall()

  connection.commit()
  connection.close()

  if user:
    return True
  else:
    return False

def create_user(username, password):
  connection = sqlite3.connect('server.db')
  cursor = connection.cursor()

  info = (username, password)
  cursor.execute("INSERT INTO users VALUES(?, ?)", info)

  connection.commit()
  connection.close()

def remove_user_from_database(username, password):
    connection = sqlite3.connect('server.db')
    cursor = connection.cursor()
    info = (username, password)
    cursor.execute("DELETE FROM users WHERE username = ? and password = ?", info)
    connection.commit()
    connection.close()

def log(username, event_type, path, dest=None):
  with open(username + ".log", "a") as f:
    time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dest_path = ""
    if dest is not None:
      dest_path = " to " + dest
    f.write(time + " " + event_type + ": "  + path + dest_path + "\n")