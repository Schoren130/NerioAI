from agents import function_tool  # type: ignore
from flask import session
from globals import pending_commands, command_results
import time

@function_tool
def send_command(command: str) -> str:
    print("Yes")
    try:
        global session
        username = session.get("username", None)
        global pending_commands
        pending_commands[username]= command
        print(username)
        print(pending_commands)
        #print(command_results[username])
        print("b")

        start_time = time.time()
        timeout= 20

        while command_results.get(username) is None:
            if time.time() - start_time >= timeout:
                return ("Keine Antwort erhalten. Vieleicht hat der User nicht die App sondern benutzt den servic im Browser(ein Grund). Frage nach ob er die App hat.")
            print("waiting")
            pass
        print("h")
        result=command_results.pop(username, None)
        print("result:")
        print(result)
        print("hatfunktioniert")
        return(result)

    except Exception as e:
        print("error")
        print(e)

#send_command(input("test"))