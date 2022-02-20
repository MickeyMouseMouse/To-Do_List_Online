from flask import Flask, request
from flask_restx import Api, fields, Resource
from Database import User, Folder, Task
import jwt, datetime, logging, bcrypt
from functools import wraps


app = Flask(__name__)
app.secret_key = "F1M%7rJxvdi56-jZC%859uq6N(o&N24f9u)1(ryI"

api = Api(app)

token_model = api.model("token", {
	"token": fields.String,
	"expire": fields.Integer
	})
task_model = api.model("task", {
	"task_content": fields.String,
	"task_deadline": fields.String,
	"task_priority": fields.String
	})


def create_token(username, lifetime_minutes = 30):
	expire = datetime.datetime.utcnow() + datetime.timedelta(minutes = lifetime_minutes)
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
			return "Invalid request", 400
		try:
			username = jwt.decode(request.form["token"], app.secret_key,
							algorithms = ["HS256"])["username"]
			user = User.get_or_none(User.username == username)
			if not user:
				return "There is no such user", 410
		except jwt.InvalidTokenError:
			app.logger.info(f"JWT validation failed [{username}]")
			return "Invalid token", 403
		return f(*args, **kwargs, user = user)
	return wrapped


@api.route("/update_token")
class UpdateToken(Resource):
	@check_token
	@api.doc(params = {"token": "<token>"})
	@api.response(200, "<token object>", token_model)
	@api.response(403, "Invalid token")
	@api.response(410, "There is no such user")
	def post(self, user):
		app.logger.info(f"Token updated [{user.username}]")
		return create_token(user.username), 200


@api.route("/registration")
class UserRegistration(Resource):
	@api.doc(params = {"username": "<username>", "password": "<password>"})
	@api.response(200, "<token object>", token_model)
	@api.response(400, "Invalid request")
	@api.response(401, "This username is already taken")
	def post(self):
		f = request.form
		if not ("username" in f and "password" in f):
			return "Invalid request", 400
		
		user = User.get_or_none(User.username == f['username'])
		if user:
			app.logger.info(f"Registration failed [{f['username']}]")
			return "This username is already taken", 401
		new_user = User.create(username = f["username"],
			password = bcrypt.hashpw(f["password"].encode(), bcrypt.gensalt()))
		Folder.create(folder_name = "Default", user_id = new_user.user_id)
		
		app.logger.info(f"Successfully registered [{f['username']}]")
		return create_token(f['username']), 200


@api.route("/login")
class UserLogin(Resource):
	@api.doc(params = {"username": "<username>", "password": "<password>"})
	@api.response(200, "<token object>", token_model)
	@api.response(400, "Invalid request")
	@api.response(401, "The username or password is incorrect")
	def post(self):
		f = request.form
		if not ("username" in f and "password" in f):
			return "Invalid request", 400
		
		user = User.get_or_none(User.username == f["username"])
		if user:
			if bcrypt.checkpw(f["password"].encode(), user.password):
				app.logger.info(f"Logged in successfully [{f['username']}]")
				return create_token(f["username"]), 200
			
		app.logger.info(f"Failed to log in [{f['username']}]")
		return "The username or password is incorrect", 401


@api.route("/get_folders")
class GetFolders(Resource):
	@check_token
	@api.doc(params = {"token": "<token>"})
	@api.response(200, "<list of strings (folder names)>")
	@api.response(403, "Invalid token")
	@api.response(410, "There is no such user")
	def post(self, user):
		result = []
		for el in list(Folder.select().where(Folder.user_id == user.user_id)):
			result.append(el.folder_name)
		return result, 200


@api.route("/create_folder")
class CreateFolder(Resource):
	@check_token
	@api.doc(params = {"token": "<token>", "folder_name": "<folder_name>"})
	@api.response(200, "The folder created")
	@api.response(400, "Invalid request")
	@api.response(403, "Invalid token")
	@api.response(409, "The folder already exists")
	@api.response(410, "There is no such user")
	def post(self, user):
		f = request.form
		if not "folder_name" in f:
			return "Invalid request", 400
	
		folder = Folder.get_or_none(Folder.user_id == user.user_id,
								Folder.folder_name == f["folder_name"])
		if folder:
			return "The folder already exists", 409
		Folder.create(user_id = user.user_id, folder_name = f["folder_name"])
		return "The folder created", 200


@api.route("/delete_folder")
class DeleteFolder(Resource):
	@check_token
	@api.doc(params = {"token": "<token>", "folder_number": "<folder_number>"})
	@api.response(200, "The folder deleted")
	@api.response(400, "Invalid request")
	@api.response(403, "Invalid token")
	@api.response(404, "There is no such folder")
	@api.response(410, "There is no such user")
	def post(self, user):
		f = request.form
		if not "folder_number" in f:
			return "Invalid request", 400
	
		try:
			list(Folder.select()
				.where(Folder.user_id == user.user_id)) \
					[int(f["folder_number"])].delete_instance()
			return "The folder deleted", 200
		except:
			return "There is no such folder", 404	


@api.route("/rename_folder")
class RenameFolder(Resource):
	@check_token
	@api.doc(params = {"token": "<token>", "folder_number": "<folder_number>"})
	@api.response(200, "The folder renamed")
	@api.response(400, "Invalid request")
	@api.response(403, "Invalid token")
	@api.response(404, "There is no such folder")
	@api.response(410, "There is no such user")
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "new_name" in f):
			return "Invalid request", 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			folder.folder_name = f["new_name"]
			folder.save()
			return "The folder renamed", 200
		except:
			return "There is no such folder", 404


@api.route("/get_tasks")
class GetTasks(Resource):
	@check_token
	@api.doc(params = {"token": "<token>", "folder_number": "<folder_number>"})
	@api.response(200, "<task object>", task_model)
	@api.response(400, "Invalid request")
	@api.response(403, "Invalid token")
	@api.response(404, "There is no such folder")
	@api.response(410, "There is no such user")
	def post(self, user):
		f = request.form
		if not "folder_number" in f:
			return "Invalid request", 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			tasks = Task.select().where(Task.folder_id == folder.folder_id).dicts().execute()
			result = []
			for el in tasks:
				result.append({"task_content": el["task_content"],
							"task_deadline": el["task_deadline"],
							"task_priority": el["task_priority"]})
			return result, 200
		except:
			return "There is no such folder", 404


@api.route("/new_task")
class NewTask(Resource):
	@check_token
	@api.doc(params = {"token": "<token>", "folder_number": "<folder_number>",
		"task_content": "<task_content>", "task_deadline": "<task_deadline>",
		"task_proirity": "<task_proirity>"})
	@api.response(200, "The task added")
	@api.response(400, "Invalid request")
	@api.response(403, "Invalid token")
	@api.response(404, "There is no such folder")
	@api.response(410, "There is no such user")
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "task_content" in f and
			"task_deadline" in f and "task_priority" in f):
			return "Invalid request", 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			Task.create(folder_id = folder.folder_id, task_content = f["task_content"],
				task_deadline = f["task_deadline"], task_priority = f["task_priority"])
			return "The task added", 200
		except:
			return "There is no such folder", 404


@api.route("/remove_task")
class RemoveTask(Resource):
	@check_token
	@api.doc(params = {"token": "<token>", "folder_number": "<folder_number>", 
		"task_number": "<task_number>", "task_content": "<task_content>",
		"task_deadline": "<task_deadline>", "task_proirity": "<task_proirity>"})
	@api.response(200, "The task removed")
	@api.response(400, "Invalid request")
	@api.response(403, "Invalid token")
	@api.response(404, "There is no such task")
	@api.response(410, "There is no such user")
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "task_number" in f):
			return "Invalid request", 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			list(Task.select()
				.where(Task.folder_id == folder.folder_id)) \
					[int(f["task_number"])].delete_instance()
			return "The task removed", 200
		except:
			return "There is no such task", 404


@api.route("/update_task")
class UpdateTask(Resource):
	@check_token
	@api.doc(params = {"token": "<token>", "folder_number": "<folder_number>", 
		"task_number": "<task_number>", "task_content": "<task_content>", 
		"task_deadline": "<task_deadline>", "task_priority": "<task_proirity>"})
	@api.response(200, "The task updated")
	@api.response(400, "Invalid request")
	@api.response(403, "Invalid token")
	@api.response(404, "There is no such task")
	@api.response(410, "There is no such user")
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "task_number" in f and
			"task_content" in f and "task_deadline" in f and "task_priority" in f):
			return "Invalid request", 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			task = list(Task.select()
				.where(Task.folder_id == folder.folder_id))[int(f["task_number"])]
			task.task_content = f["task_content"]
			task.task_deadline = f["task_deadline"]
			task.task_priority = f["task_priority"]
			task.save()
			return "The task updated", 200
		except:
			return "There is no such task", 404


if __name__ == "__main__":
	logging.basicConfig(filename = "ToDoList.log", level = logging.DEBUG,
		format = "[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
	
	app.run(host = "localhost", port = 5000)
