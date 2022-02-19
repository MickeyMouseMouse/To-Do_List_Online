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


class Folder(BaseModel):
	folder_id = AutoField(column_name = "folder_id")
	user_id = ForeignKeyField(User)
	folder_name = TextField(column_name = "folder_name")

	class Meta:
		table_name = "Folders"


class Task(BaseModel):
	task_id = AutoField(column_name = "task_id")
	folder_id = ForeignKeyField(Folder)
	task_content = TextField(column_name = "task_content")
	task_deadline = TextField(column_name = "task_deadline")
	task_priority = TextField(column_name = "task_priority")

	class Meta:
		table_name = "Tasks"


if not exists:
	User.create_table()
	Folder.create_table()
	Task.create_table()