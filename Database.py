from pathlib import Path
from peewee import SqliteDatabase, Model, AutoField, TextField, BlobField, ForeignKeyField

# https://peewee.readthedocs.io/en/latest/peewee/playhouse.html#migrate
# from playhouse.migrate import SqliteMigrator


DATABASE = "ToDoList.db"
exists = Path(DATABASE).exists()
db = SqliteDatabase(DATABASE)


class BaseModel(Model):
	class Meta:
		database = db


class User(BaseModel):
	user_id = AutoField(column_name = "user_id")
	username = TextField(column_name = "username", unique = True)
	password = BlobField(column_name = "password")
	
	class Meta:
		table_name = "Users"


class List(BaseModel):
	list_id = AutoField(column_name = "list_id")
	list_name = TextField(column_name = "list_name")
	user_id = ForeignKeyField(User)

	class Meta:
		table_name = "Lists"


class Task(BaseModel):
	task_id = AutoField(column_name = "task_id")
	task_content = TextField(column_name = "task_content")
	task_deadline = TextField(column_name = "task_deadline")
	task_priority = TextField(column_name = "task_priority")
	list_id = ForeignKeyField(List)

	class Meta:
		table_name = "Tasks"


if not exists:
	User.create_table()
	List.create_table()
	Task.create_table()