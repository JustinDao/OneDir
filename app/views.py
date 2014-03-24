from app import app
from flask import request
import sqlite3
import os
import shutil



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

@app.route('/check_username', methods=['POST'])
def check_username_request():
  if user_exists(request.form['username']):
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
    os.rename(src, dest)

    if os.path.isfile(dest):
      return "File moved."
    elif os.path.isdir(dest):
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
      return "File deleted."
    elif os.path.isdir(filepath):
      shutil.rmtree(filepath)
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
      return "Directory created"
    return "Directory already exists"

  return "Failed to create directory."


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

def create_user(username, password):
  connection = sqlite3.connect('server.db')
  cursor = connection.cursor()

  info = (username, password)
  cursor.execute("INSERT INTO users VALUES(?, ?)", info)

  connection.commit()
  connection.close()