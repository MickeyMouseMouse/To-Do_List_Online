import requests, re, datetime
from getpass import getpass


def check_server_address(address):
	return re.fullmatch("^http(s|):\/\/((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4]" +
					"[0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4]" +
					"[0-9]|25[0-5])|localhost):[0-9]+\/$", address)


def check_cmd(string):
	string = string.strip()
	
	if re.match("^(help|\?|login|reg|exit|folders|f)$", string):
		return [string]
	
	m = re.match("^create( )+(?P<folder_name>[A-Za-z0-9]+)$", string) 
	if m:
		return ["create", m.group("folder_name")]
	
	m = re.match("^delete( )+(?P<folder_number>[1-9]+)$", string) 
	if m:
		return ["delete", int(m.group("folder_number"))]
	
	m = re.match("^rename( )+(?P<folder_number>[1-9]+)( )+(?P<new_name>[A-Za-z0-9]+)$", string) 
	if m:
		return ["rename", int(m.group("folder_number")), m.group("new_name")]

	m = re.match("^(tasks|t)( )+(?P<folder_number>[1-9]+)$", string) 
	if m:
		return ["tasks", int(m.group("folder_number"))]
	
	m = re.match("^new( )+(?P<folder_number>[1-9]+)$", string) 
	if m:
		return ["new", int(m.group("folder_number"))]
	
	m = re.match("^rm( )+(?P<folder_number>[1-9]+)( )+(?P<task_number>[1-9]+)$", string) 
	if m:
		return ["rm", int(m.group("folder_number")), int(m.group("task_number"))]
	
	m = re.match("^update( )+(?P<folder_number>[1-9]+)( )+(?P<task_number>[1-9]+)$", string) 
	if m:
		return ["update", int(m.group("folder_number")), int(m.group("task_number"))]
	
	return [""]


def post(route, args = None):
	try:
		return requests.post(addr + route, args)
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
	print("FOLDERS COMMANDS:")
	print("  folders or f")
	print("  create <folder name>")
	print("  delete <folder number>")
	print("  rename <folder number> <new folder name>\n")
	print("TASKS COMMANDS:")
	print("  tasks <folder number> or t <folder number>")
	print("  new <folder number>")
	print("  rm <folder number> <task number>")
	print("  update <folder number> <task number>\n")
	print("OTHER:")
	print("  help, exit")
	
	
if __name__ == "__main__":
	addr = input("Server: ")
	if len(addr) == 0:
		addr = "http://127.0.0.1:5000/"
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
						for i in range(len(folders)):
							print(f"{i + 1}. {folders[i]}")
			case "create":
				print(post("create_folder", {
					"token": token,
					"folder_name": cmd[1]
					}).json()["message"])
			case "delete":
				print(post("delete_folder", {
					"token": token,
					"folder_number": cmd[1] - 1
					}).json()["message"])
			case "rename":
				print(post("rename_folder", {
					"token": token,
					"folder_number": cmd[1] - 1,
					"new_name": cmd[2]
					}).json()["message"])
			case "tasks" | "t":
				response = post("get_tasks", {
					"token": token,
					"folder_number": cmd[1] - 1
					})
				answer = response.json()
				if response.status_code != 200:
					print(answer["message"])
				else:
					tasks = answer["task_list"]
					if len(tasks) == 0:
						print("No tasks")
					else:
						for i in range(len(tasks)):
							print(f"{i + 1}.\n" +
								f" Content: {tasks[i]['task_content']}\n" +
								f" Deadline: {tasks[i]['task_deadline']}\n" +
								f" Priority: {tasks[i]['task_priority']}")
			case "new":
				response = post("new_task", {
					"token": token,
					"folder_number": cmd[1] - 1,
					"task_content": input("Content: "),
					"task_deadline": input("Deadline: "),
					"task_priority": input("Priority: ")
					})
				print(f"\n{response.json()['message']}")
			case "rm":
				response = post("remove_task", {
					"token": token,
					"folder_number": cmd[1] - 1,
					"task_number": cmd[2] - 1
					})
				print(f"\n{response.json()['message']}")
			case "update":
				response = post("update_task", {
					"token": token,
					"folder_number": cmd[1] - 1,
					"task_number": cmd[2] - 1,
					"task_content": input("Content: "),
					"task_deadline": input("Deadline: "),
					"task_priority": input("Priority: ")
					})
				print(f"\n{response.json()['message']}")
			case "help" | "?":
				print_help()
			case "exit":
				exit()
			case _:
				print("Invalid command (try 'help')")
		
		if token_expire - datetime.datetime.utcnow().timestamp() < \
				datetime.timedelta(minutes = 5).total_seconds():
			update_jwt()