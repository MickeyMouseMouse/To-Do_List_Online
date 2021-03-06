from flask import Flask, request
from flask_restx import Api, fields, Resource
from flask_restx.reqparse import RequestParser
from Database import User, Folder, Task
import jwt, datetime, logging, bcrypt
from functools import wraps


app = Flask(__name__)
app.secret_key = "F1M%7rJxvdi56-jZC%859uq6N(o&N24f9u)1(ryI"
logging.basicConfig(filename = "ToDoList.log", level = logging.DEBUG, 
	format = "[%(asctime)s] %(levelname)s - %(message)s")
		
api = Api(
	app,
	version = "1.0",
	title = "ToDoList Service API",
	default = "ToDoList"
)

message_model = api.model("message", {
	"message": fields.String
})
list_model = api.model("list", {
	"list": fields.List(fields.String)
})
token_model = api.model("token", {
	"token": fields.String,
	"expire": fields.Integer
})
task_list_model = api.model("task_list", {
	"task_list": fields.List(fields.Nested(
		api.model("task", {
			"task_content": fields.String,
			"task_deadline": fields.String,
			"task_priority": fields.String
		}),
		skip_none = True
	))
})


def create_token(username, lifetime_minutes = 30):
	expire = datetime.datetime.utcnow() + datetime.timedelta(
		minutes = lifetime_minutes)
	token = jwt.encode(
		{"username": username, "exp": expire},
		app.secret_key,
		algorithm = "HS256"
	)
	if isinstance(token, bytes):
		token = token.decode()
	return {"token": token, "expire": expire.timestamp()}


def check_token(f):
	@wraps(f)
	def wrapped(*args, **kwargs):
		if "token" not in request.form:
			return {"message": "Invalid request"}, 400
		try:
			username = jwt.decode(request.form["token"], app.secret_key,
							algorithms = ["HS256"])["username"]
			user = User.get_or_none(User.username == username)
			if not user:
				return {"message": "There is no such user"}, 410
		except jwt.InvalidTokenError:
			return {"message": "Invalid token"}, 403
		return f(*args, **kwargs, user = user)
	return wrapped


@api.route("/update_token")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
)
class UpdateToken(Resource):
	@api.response(200, "Success", token_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		return create_token(user.username), 200


@api.route("/registration")
@api.expect(RequestParser()
	.add_argument(name = "username", type = str, location = "form")
	.add_argument(name = "password", type = str, location = "form")
)
class UserRegistration(Resource):
	@api.response(200, "Success", token_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(401, "This username is already taken", message_model)
	def post(self):
		f = request.form
		if not ("username" in f and "password" in f):
			return {"message": "Invalid request"}, 400
		
		user = User.get_or_none(User.username == f['username'])
		if user:
			return {"message": "This username is already taken"}, 401
		new_user = User.create(username = f["username"],
			password = bcrypt.hashpw(f["password"].encode(), bcrypt.gensalt()))
		Folder.create(folder_name = "Default", user_id = new_user.user_id)
		
		return create_token(f['username']), 200


@api.route("/login")
@api.expect(RequestParser()
	.add_argument(name = "username", type = str, location = "form")
	.add_argument(name = "password", type = str, location = "form")
)
class UserLogin(Resource):
	@api.response(200, "Success", token_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(401, "The username or password is incorrect", message_model)
	def post(self):
		f = request.form
		if not ("username" in f and "password" in f):
			return {"message": "Invalid request"}, 400
		
		user = User.get_or_none(User.username == f["username"])
		if user:
			if bcrypt.checkpw(f["password"].encode(), user.password):
				return create_token(f["username"]), 200
		
		return {"message": "The username or password is incorrect"}, 401


@api.route("/get_folders")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
)
class GetFolders(Resource):
	@api.response(200, "Success", list_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		result = []
		for el in list(Folder.select().where(Folder.user_id == user.user_id)):
			result.append(el.folder_name)
		return {"list": result}, 200


@api.route("/create_folder")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
	.add_argument(name = "folder_name", type = str, location = "form")
)
class CreateFolder(Resource):
	@api.response(200, "The folder created", message_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(409, "The folder already exists", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		f = request.form
		if not "folder_name" in f:
			return {"message": "Invalid request"}, 400
	
		folder = Folder.get_or_none(Folder.user_id == user.user_id,
								Folder.folder_name == f["folder_name"])
		if folder:
			return {"message": "The folder already exists"}, 409
		Folder.create(user_id = user.user_id, folder_name = f["folder_name"])
		return {"message": "The folder created"}, 200


@api.route("/delete_folder")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
	.add_argument(name = "folder_number", type = int, location = "form")
)
class DeleteFolder(Resource):
	@api.response(200, "The folder deleted", message_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(404, "There is no such folder", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		f = request.form
		if not "folder_number" in f:
			return {"message": "Invalid request"}, 400
	
		try:
			folder = list(Folder.select()
						.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			for task in list(Task.select().where(Task.folder_id == folder.folder_id)):
				task.delete_instance()
			folder.delete_instance()
			return {"message": "The folder deleted"}, 200
		except:
			return {"message": "There is no such folder"}, 404	


@api.route("/rename_folder")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
	.add_argument(name = "folder_number", type = int, location = "form")
	.add_argument(name = "new_name", type = str, location = "form")
)
class RenameFolder(Resource):
	@api.response(200, "The folder renamed", message_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(404, "There is no such folder", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "new_name" in f):
			return {"message": "Invalid request"}, 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			folder.folder_name = f["new_name"]
			folder.save()
			return {"message": "The folder renamed"}, 200
		except:
			return {"message": "There is no such folder"}, 404


@api.route("/get_tasks")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
	.add_argument(name = "folder_number", type = int, location = "form")
)
class GetTasks(Resource):
	@api.response(200, "Success", task_list_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(404, "There is no such folder", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		f = request.form
		if not "folder_number" in f:
			return {"message": "Invalid request"}, 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			tasks = Task.select().where(Task.folder_id == folder.folder_id).dicts().execute()
			result = []
			for el in tasks:
				result.append({
					"task_content": el["task_content"],
					"task_deadline": el["task_deadline"],
					"task_priority": el["task_priority"]
				})
			return {"task_list": result}, 200
		except:
			return {"message": "There is no such folder"}, 404


@api.route("/new_task")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
	.add_argument(name = "folder_number", type = int, location = "form")
	.add_argument(name = "task_content", type = str, location = "form")
	.add_argument(name = "task_deadline", type = str, location = "form")
	.add_argument(name = "task_priority", type = str, location = "form")
)
class NewTask(Resource):
	@api.response(200, "The task added", message_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(404, "There is no such folder", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "task_content" in f and
			"task_deadline" in f and "task_priority" in f):
			return {"message": "Invalid request"}, 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			Task.create(folder_id = folder.folder_id, task_content = f["task_content"],
				task_deadline = f["task_deadline"], task_priority = f["task_priority"])
			return {"message": "The task added"}, 200
		except:
			return {"message": "There is no such folder"}, 404


@api.route("/remove_task")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
	.add_argument(name = "folder_number", type = int, location = "form")
	.add_argument(name = "task_number", type = int, location = "form")
)
class RemoveTask(Resource):
	@api.response(200, "The task removed", message_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(404, "There is no such task", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "task_number" in f):
			return {"message": "Invalid request"}, 400
	
		try:
			folder = list(Folder.select()
				.where(Folder.user_id == user.user_id))[int(f["folder_number"])]
			list(Task.select()
				.where(Task.folder_id == folder.folder_id)) \
					[int(f["task_number"])].delete_instance()
			return {"message": "The task removed"}, 200
		except:
			return {"message": "There is no such task"}, 404


@api.route("/update_task")
@api.expect(RequestParser()
	.add_argument(name = "token", type = str, location = "form")
	.add_argument(name = "folder_number", type = int, location = "form")
	.add_argument(name = "task_number", type = int, location = "form")
	.add_argument(name = "new_folder_number", type = int, location = "form")
	.add_argument(name = "new_content", type = str, location = "form")
	.add_argument(name = "new_deadline", type = str, location = "form")
	.add_argument(name = "new_priority", type = str, location = "form")
)
class UpdateTask(Resource):
	@api.response(200, "The task updated", message_model)
	@api.response(400, "Invalid request", message_model)
	@api.response(403, "Invalid token", message_model)
	@api.response(404, "There is no such task", message_model)
	@api.response(410, "There is no such user", message_model)
	@check_token
	def post(self, user):
		f = request.form
		if not ("folder_number" in f and "task_number" in f and
			"new_folder_number" in f and "new_content" in f and
			"new_deadline" in f and "new_priority" in f):
			return {"message": "Invalid request"}, 400
	
		try:
			folders = list(Folder.select().where(Folder.user_id == user.user_id))
			current_folder = folders[int(f["folder_number"])]
			new_folder = folders[int(f["new_folder_number"])]
			task = list(Task.select()
				.where(Task.folder_id == current_folder.folder_id))[int(f["task_number"])]
			
			task.folder_id = new_folder.folder_id
			task.task_content = f["new_content"]
			task.task_deadline = f["new_deadline"]
			task.task_priority = f["new_priority"]
			task.save()
			return {"message": "The task updated"}, 200
		except:
			return {"message": "There is no such task"}, 404


if __name__ == "__main__":	
	app.run(host = "0.0.0.0", port = 8000)
