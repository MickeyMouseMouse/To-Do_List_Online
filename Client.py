import requests, re, datetime
from getpass import getpass


def check_server_address(address):
	return re.fullmatch("^http(s|):\/\/(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4]" +
					"[0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4]" +
					"[0-9]|25[0-5]):[0-9]+$", address)


def check_cmd(string):
	string = string.strip()
	
	if re.match("^(help|\?|login|reg|exit|lists|new)$", string):
		return [string]
	
	m = re.match("^(?P<cmd>create|delete)( )+(?P<name>[A-Za-z0-9]+)$", string) 
	if m:
		return [m.group("cmd"), m.group("name")]
	
	m = re.match("^rename( )+(?P<current>[A-Za-z0-9]+)( )+(?P<new>[A-Za-z0-9]+)$", string) 
	if m:
		return ["rename", m.group("current"), m.group("new")]

	m = re.match("^tasks( )+(?P<name>[A-Za-z0-9]+)$", string) 
	if m:
		return ["tasks", m.group("name")]
	
	m = re.match("^rm( )+(?P<id>[0-9]+)$", string) 
	if m:
		return ["rm", m.group("id")]
	
	m = re.match("^update( )+(?P<id>[0-9]+)$", string) 
	if m:
		return ["update", m.group("id")]
	
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
	if response.status_code == 200:
		global token, token_timeout
		json = response.json()
		token = json["token"]
		token_timeout = json["timeout"]
		print("You are logged in")
		return True
	else:
		print(response.text)
		return False


def registration():
	print("Enter a username and password to register a new account.")
	username = input("Username: ")
	password = getpass()
	response = post("registration", {"username": username, "password": password})
	if response.status_code == 200:
		global token, token_timeout
		json = response.json()
		token = json["token"]
		token_timeout = json["timeout"]
		print("You are registered")
		return True
	else:
		print(response.text)
		return False


def update_jwt():
	global token, token_timeout
	response = post("update_token", {"token": token})
	if response.status_code == 200:
		json = response.json()
		token = json["token"]
		token_timeout = json["timeout"]
	

def print_help():
	print("Commands:")
	print("  help, exit\n")
	print("  lists")
	print("  create <list name>")
	print("  delete <list name>")
	print("  rename <current list name> <new list name>\n")
	print("  tasks <list name>")
	print("  new")
	print("  rm <task id>")
	print("  update <task id>")
	
	
if __name__ == "__main__":
	addr = input("Server: ")
	if len(addr) == 0:
		addr = "http://127.0.0.1:5000/"
	else:
		if not check_server_address(addr):
			exit("Invalid server address")
	
	global token, token_timeout
	
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
		
		if token_timeout - datetime.datetime.utcnow().timestamp() < \
				datetime.timedelta(minutes = 5).total_seconds():
			update_jwt()
		
		match cmd[0]:
			case "lists":
				response = post("lists", {"token": token})
				if response.status_code != 200:
					print(response.text)
				else:
					lists = response.json()
					if len(lists) == 0:
						print("No lists")
					else:
						for list_name in lists:
							print(list_name)
			case "create":
				print(post("create_list", {
					"token": token,
					"list_name": cmd[1]
					}).text)
			case "delete":
				print(post("delete_list", {
					"token": token,
					"list_name": cmd[1]
					}).text)
			case "rename":
				print(post("rename_list", {
					"token": token,
					"current": cmd[1],
					"new": cmd[2]
					}).text)
			case "tasks":
				response = post("tasks", {
					"token": token,
					"list_name": cmd[1]
					})
				if response.status_code != 200:
					print(response.text)
				else:
					tasks = response.json()
					if len(tasks) == 0:
						print("No tasks")
					else:
						for i in range(len(tasks)):
							print(f"{i}. (task_id = {tasks[i]['task_id']})\n" +
								f"Content: {tasks[i]['task_content']}\n" +
								f"Deadline: {tasks[i]['task_deadline']}\n" +
								f"Priority: {tasks[i]['task_priority']}")
			case "new":
				response = post("new_task", {
					"token": token,
					"task_content": input("Content: "),
					"task_deadline": input("Deadline: "),
					"task_priority": input("Priority: "),
					"list_name": input("List: ")
					})
				print(f"\n{response.text}")
			case "rm":
				response = post("rm_task", {
					"token": token,
					"task_id": cmd[1]
					})
				print(f"\n{response.text}")
			case "update":
				response = post("update_task", {
					"token": token,
					"task_id": cmd[1],
					"task_content": input("Content: "),
					"task_deadline": input("Deadline: "),
					"task_priority": input("Priority: ")
					})
				print(f"\n{response.text}")
			case "help" | "?":
				print_help()
			case "exit":
				exit()
			case _:
				print("Invalid command (try 'help')")
		