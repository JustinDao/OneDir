from app import app
from flask import request

@app.route('/')
@app.route('/index')
def index():
  return "Hello, World!"

@app.route('/login', methods=['POST'])
def login():
  if valid_login(request.form['username'], request.form['password']):
    return "Valid!"
  else:
    return "Not Valid :("
   

def valid_login(username, password):
  if username == "tjd5at" and password == "hunter2":
    return True
  else:
    return False