import requests, re, datetime, prettytable as pt
from getpass import getpass


def check_server_address(address):
	return re.fullmatch("^http(s|):\/\/(.)+\/$", address)

def check_cmd(string):
	string = string.strip()
	
	if re.match("^(\?|login|reg|exit|folders|f|new)$", string):
		return [string]
	
	m = re.match("^create( )+(?P<folder_name>[A-Za-z0-9]+)$", string) 
	if m:
		return ["create", m.group("folder_name")]
	
	m = re.match("^delete( )+(?P<folder_number>[0-9]+)$", string) 
	if m:
		return ["delete", m.group("folder_number")]
	
	m = re.match("^rename( )+(?P<folder_number>[0-9]+)( )+(?P<new_name>[A-Za-z0-9]+)$", string) 
	if m:
		return ["rename", m.group("folder_number"), m.group("new_name")]

	m = re.match("^(tasks|t)( )+(?P<folder_number>[0-9]+)$", string) 
	if m:
		return ["tasks", m.group("folder_number")]
	
	m = re.match("^rm( )+(?P<folder_number>[0-9]+)( )+(?P<task_number>[0-9]+)$", string) 
	if m:
		return ["rm", m.group("folder_number"), m.group("task_number")]
	
	m = re.match("^update( )+(?P<folder_number>[0-9]+)( )+(?P<task_number>[0-9]+)$", string) 
	if m:
		return ["update", m.group("folder_number"), m.group("task_number")]
	
	return [""]


def post(route, args = None):
	try:
		return requests.post(addr + route, args, verify = False)
	except requests.exceptions.ConnectionError:
		exit("Server is disconnected")


def login():
	username = input("Username: ")
	password = getpass()
	response = post("login", {"username": username, "password": password})
	answer = response.json()
	if response.status_code == 200:
		global token, token_expire
		token = answer["token"]
		token_expire = answer["expire"]
		print("You are logged in")
		return True
	else:
		print(answer["message"])
		return False


def registration():
	print("Enter a username and password to register a new account.")
	username = input("Username: ")
	password = getpass()
	response = post("registration", {"username": username, "password": password})
	answer = response.json()
	if response.status_code == 200:
		global token, token_expire
		token = answer["token"]
		token_expire = answer["expire"]
		print("You are registered")
		return True
	else:
		print(answer["message"])
		return False


def update_jwt():
	global token, token_expire
	response = post("update_token", {"token": token})
	answer = response.json()
	if response.status_code == 200:
		token = answer["token"]
		token_expire = answer["expire"]
	else:
		print(answer["message"])
	

def print_help():		
	table = pt.PrettyTable()
	table.field_names = ["COMMAND", "DESCRIPTION"]
	table.add_rows([
		["folders or f", "Show all folders"],
		["create <folder name>", "Create a new folder"],
		["delete <folder number>", "Delete the folder"],
		["rename <folder number> <new name>", "Rename the folder"],
		["tasks or t <folder number>", "Show all tasks in folder"],
		["new", "Create a new task in the folder"],
		["rm <folder number> <task number>", "Remove the task"],
		["update <folder number> <task number>", "Update the task"],
		["?", "Show help"],
		["exit", "Exit the script"]
	])
	table.align = "l"
	print(table)
	
if __name__ == "__main__":
	addr = input("Server: ")
	if len(addr) == 0:
		addr = "https://to-do-list-project.duckdns.org/" # "http://127.0.0.1:8000/"
	else:
		if not check_server_address(addr):
			exit("Invalid server address (example: http://127.0.0.1:5000/)")
	
	global token, token_expire
	
	while True:
		cmd = check_cmd(input("\n>> "))
		match cmd[0]:
			case "login":
				if login():
					break
			case "reg":
				if registration():
					break
			case "exit":
				exit()
			case _:
				print("Invalid command ('login', 'reg' or 'exit')")

	while True:
		cmd = check_cmd(input("\n>> "))	
		match cmd[0]:
			case "folders" | "f":
				response = post("get_folders", {"token": token})
				answer = response.json()
				if response.status_code != 200:
					print(answer["message"])
				else:
					folders = answer["list"]
					if len(folders) == 0:
						print("No folders")
					else:
						table = pt.PrettyTable()
						table.field_names = ["???", "FOLDER NAME"]
						for i in range(len(folders)):
							table.add_row([i, folders[i]])
						table.align = "l"
						print(table)
			case "create":
				print(post("create_folder", {
					"token": token,
					"folder_name": cmd[1]
					}).json()["message"])
			case "delete":
				print(post("delete_folder", {
					"token": token,
					"folder_number": cmd[1]
					}).json()["message"])
			case "rename":
				print(post("rename_folder", {
					"token": token,
					"folder_number": cmd[1],
					"new_name": cmd[2]
					}).json()["message"])
			case "tasks" | "t":
				response = post("get_tasks", {
					"token": token,
					"folder_number": cmd[1]
					})
				answer = response.json()
				if response.status_code != 200:
					print(answer["message"])
				else:
					tasks = answer["task_list"]
					if len(tasks) == 0:
						print("No tasks")
					else:
						table = pt.PrettyTable(hrules = pt.ALL)
						table.field_names = ["???", "TASK"]
						for i in range(len(tasks)):
							nested_table = pt.PrettyTable(header = False, hrules = pt.ALL)
							nested_table.add_rows([
								["Content", tasks[i]["task_content"]],
								["Deadline", tasks[i]["task_deadline"]],
								["Priority", tasks[i]["task_priority"]],
							])
							table.add_row([i, nested_table])
						print(table)
			case "new":
				response = post("new_task", {
					"token": token,
					"folder_number": input("Folder number: "),
					"task_content": input("Content: "),
					"task_deadline": input("Deadline: "),
					"task_priority": input("Priority: ")
					})
				print(f"\n{response.json()['message']}")
			case "rm":
				response = post("remove_task", {
					"token": token,
					"folder_number": cmd[1],
					"task_number": cmd[2]
					})
				print(f"\n{response.json()['message']}")
			case "update":
				response = post("update_task", {
					"token": token,
					"folder_number": cmd[1],
					"task_number": cmd[2],
					"new_folder_number": input("New folder number: "),
					"new_content": input("New content: "),
					"new_deadline": input("New deadline: "),
					"new_priority": input("New priority: ")
					})
				print(f"\n{response.json()['message']}")
			case "?":
				print_help()
			case "exit":
				exit()
			case _:
				print("Invalid command (try '?')")
		
		if token_expire - datetime.datetime.utcnow().timestamp() < \
				datetime.timedelta(minutes = 5).total_seconds():
			update_jwt()