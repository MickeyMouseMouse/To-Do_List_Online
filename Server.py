from flask import Flask, request, jsonify
from Database import User, List, Task
import jwt, datetime, logging, bcrypt
from functools import wraps


app = Flask(__name__)
app.secret_key = "F1M%7rJxvdi56-jZC%859uq6N(o&N24f9u)1(ryI"


def create_token(username, timeout_in_minutes = 30):
	expire = datetime.datetime.utcnow() + datetime.timedelta(minutes = timeout_in_minutes)
	return {"token":
				jwt.encode({"username": username, "exp": expire},
				app.secret_key,
				algorithm = "HS256"),
			"expire":
				expire.timestamp()}


def check_token(f):
	@wraps(f)
	def wrapped(*args, **kwargs):
		if "token" not in request.form:
			return "Token is missing", 403
		try:
			username =  jwt.decode(request.form["token"], app.secret_key,
							algorithms = ["HS256"])["username"]
		except jwt.InvalidTokenError:
			app.logger.info(f"JWT validation failed [{username}]")
			return "Invalid token", 403
		return f(username, *args, **kwargs)
	return wrapped


@app.route("/registration", methods = ['POST'])
def registration():
	form = request.form
	if not ("username" in form and "password" in form):
		return "The username and password are required", 400
	else:
		username, password = form["username"], form["password"]
	
	user = User.get_or_none(User.username == username)
	if user:
		app.logger.info(f"Registration failed [{username}]")
		return "This username is already taken", 401
	else:
		new_user = User.create(username = username,
			password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()))
		List.create(list_name = "Default", user_id = new_user.user_id)
		
		app.logger.info(f"Successfully registered [{username}]")
		return create_token(username), 200


@app.route("/login", methods = ['POST'])
def login():
	form = request.form
	if not ("username" in form and "password" in form):
		return "The username and password are required", 400
	else:
		username, password = form["username"], form["password"]
	
	user = User.get_or_none(User.username == username)
	if user:
		if bcrypt.checkpw(password.encode(), user.password):
			app.logger.info(f"Logged in successfully [{username}]")
			return create_token(username), 200
		
	app.logger.info(f"Failed to log in [{username}]")
	return "The username or password is incorrect", 401


@app.route("/update_token", methods = ['POST'])
@check_token
def update_token(username):
	app.logger.info(f"The token updated [{username}]")
	return create_token(username), 200


@app.route("/get_lists", methods = ['POST'])
@check_token
def get_lists(username):	
	user = User.get_or_none(User.username == username)
	lists = List.select().where(List.user_id == user.user_id).dicts().execute()
	result = []
	for el in lists:
		result.append(el["list_name"])
	return jsonify(result), 200


@app.route("/create_list", methods = ['POST'])
@check_token
def create_list(username):
	form = request.form
	if not "list_name" in form:
		return "The list_name is required", 400
	else:
		list_name = form["list_name"]
	
	user = User.get_or_none(User.username == username)
	_list = List.get_or_none(List.user_id == user.user_id,
							List.list_name == list_name)
	if _list:
		return "The list already exists", 400
	else:
		List.create(list_name = list_name, user_id = user.user_id)
		return "The list added", 200


@app.route("/delete_list", methods = ['POST'])
@check_token
def delete_list(username):
	form = request.form
	if not "list_name" in form:
		return "The list_name is required", 400
	else:
		list_name = form["list_name"]
	
	user = User.get_or_none(User.username == username)
	_list = List.get_or_none(List.user_id == user.user_id,
							List.list_name == list_name)
	if not _list:
		return "The list does not exist", 400
	else:
		_list.delete_instance()
		return "The list removed", 200		


@app.route("/rename_list", methods = ['POST'])
@check_token
def rename_list(username):
	form = request.form
	if not ("current" in form and "new" in form):
		return "The current and new are required", 400
	else:
		current, new = form["current"], form["new"]
	
	user = User.get_or_none(User.username == username)
	_list = List.get_or_none(List.user_id == user.user_id,
							List.list_name == current)
	if not _list:
		return "The list does not exist", 400
	else:
		_list.list_name = new
		_list.save()
		return "The list renamed", 200		


@app.route("/get_tasks", methods = ['POST'])
@check_token
def get_tasks(username):
	form = request.form
	if not "list_name" in form:
		return "The list_name is required", 400
	else:
		list_name = form["list_name"]
	
	user = User.get_or_none(User.username == username)
	_list = List.get_or_none(List.user_id == user.user_id,
							List.list_name == list_name)
	if not _list:
		return "There is no such list", 400
	else:
		tasks = Task.select().where(Task.list_id == _list.list_id).dicts().execute()
		result = []
		for el in tasks:
			result.append({"task_id": el["task_id"],
						"task_content": el["task_content"],
						"task_deadline": el["task_deadline"],
						"task_priority": el["task_priority"]})
		return jsonify(result), 200


@app.route("/new_task", methods = ['POST'])
@check_token
def new_task(username):
	form = request.form
	if not ("task_content" in form and "task_deadline" in form and
		"task_priority" in form and "list_name" in form):
		return f"The task_content, task_deadline, task_priority and list_name are required", 400
	else:
		task_content, task_deadline = form["task_content"], form["task_deadline"]
		task_priority, list_name = form["task_priority"], form["list_name"]
	
	user = User.get_or_none(User.username == username)
	_list = List.get_or_none(List.user_id == user.user_id,
							List.list_name == list_name)
	if not _list:
		return "There is no such list", 400
	else:
		Task.create(task_content = task_content, task_deadline = task_deadline,
				task_priority = task_priority, list_id = _list.list_id)
		return "The task added", 200


@app.route("/rm_task", methods = ['POST'])
@check_token
def rm_task(username):
	form = request.form
	if not "task_id" in form:
		return "The task_id are required", 400
	else:
		task_id = form["task_id"]
	
	task = Task.get_or_none(Task.task_id == task_id)
	if not task:
		return "There is no such task", 400
	else:
		task.delete_instance()
		return "The task removed", 200


@app.route("/update_task", methods = ['POST'])
@check_token
def update_task(username):
	form = request.form
	if not ("task_id" in form and "task_content" in form and
		"task_deadline" in form and "task_priority" in form):
		return "The task_id, task_content, task_deadline and task_priority are required", 400
	else:
		task_id, task_content = form["task_id"], form["task_content"]
		task_deadline, task_priority = form["task_deadline"], form["task_priority"]
	
	task = Task.get_or_none(Task.task_id == task_id)
	if not task:
		return "There is no such task", 400
	else:
		task.task_content = task_content
		task.task_deadline = task_deadline
		task.task_priority = task_priority
		task.save()
		return "The task updated", 200


if __name__ == "__main__":
	logging.basicConfig(filename = "ToDoList.log", level = logging.DEBUG,
		format = "[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
	
	app.run(host = "localhost", port = 5000)
