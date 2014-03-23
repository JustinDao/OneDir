from app import app
from flask import request
import sqlite3



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
    return "invalid"
  else:
    return "valid"

@app.route('/create_user', methods=['POST'])
def create_user_request():
  create_user(request.form['username'], request.form['password']) 
  return "User created"

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