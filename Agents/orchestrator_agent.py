from Agents.calendar_agent import calendar_agent
from Agents.email_agent import email_agent
from Agents.tools.helpers.timefunction import get_time
from agents import Agent  # type: ignore
from Agents.tools.commands import send_command
from Agents.loxone_agent import loxone_agent

orchestrator_agent = Agent(
    name="orechstrator_agent",
    instructions=(
        "Du bist ein Meta-Agent mit Zugriff auf mehrere spezialisierte Agenten."
        "Der E-Mail-Agent kann E-Mails von bestimmten Absendern lesen und neue E-Mails schreiben mit Empfänger, Titel und Inhalt."
        "Der Kalender-Agent kann prüfen, ob im Kalender in einem Zeitraum Termine liegen, neue Termine erstellen und die nächsten 5 anstehenden Termine ausgeben (sofern kein anderes Limit angegeben ist)."
        "Nutze nur die Agenten, die wirklich nötig sind."
        "Vermeide unnötige Aufrufe und löse Aufgaben mit möglichst wenig Agenteneinsatz."
        "Immer wenn du die aktuelle Zeit brauchst(Kalender) nutze die Funktion get_time. Deine zeit ist nie aktuell sondern immer veraltet."
        "Ausßerdem kannst du mit der Funktion send_command shellbefhele an die konsole eines windows 11 pc des users senden. Wichtig!!: DAS BETRIEBSYSTEM IST WINDOWS 11 Dazu musst du nur den befhel übergeben. wenn manche befhel enicht ausgeführt wurden und der exitcode -1 zürück hat der nutzer den befhel nicht zugelassen Außerdem hat das tterminal einen verlauf, das haeißt du kannst befhele nacheinander mit zusammenhang ausfähren. du startest immer im home ordner."
        "Du hast auch ein Loxone Agent der alles um LED licht usw. mit smarthome steuert."
    ),
    model="gpt-5-mini",
    tools=[
        email_agent.as_tool(
            tool_name="Email_manager",
            tool_description="Kann emails schreiben und emails lesen eines bestimmten absenders und ungelesene emails lesen"  # noqa: E501
        ),
        calendar_agent.as_tool(
            tool_name="Calendar_manager",
            tool_description="Kann kalendereinträge machen sowie die nächsten x termine ausgeben und alle termine in einem bestimmten zeitraum ausgeben. nehme für die zeiten bitte die zeit die dir immer gegeben wird."  # noqa: E501
        ),
        get_time,
        send_command,
        loxone_agent.as_tool(
            tool_name="Lox_Smarthome_Manager",
            tool_description= "Kann alles um Smarthomes steuern"
        )
    ]
)

"Du bist ein Agent der mehrere Agents zur verfügung hat."
"Der eine Agent is tein Email agent , der Emaisls von einem bestimmten absender lesen kann und emasils mit einem empfänger titel und inhalt schreiben kann"  # noqa: E501
"Der andere Agent ist ein Kalender Agent, der schauen kann ob in einem kalender in einem bestimmten zeitraum termine hat und welche das sind. Der neue termine eintragen kann. und die naächsten 5 termine die anstehen ausgibt solange kein anderes limit festgelegt wird."  # noqa: E501
"Nutze Agenten nur, wenn du diese wirklich brauchst. Versuche so wenig Agenten wie möglich zu verwenden, um die Aufgabe zu lösen."  # noqa: E501
"Wenn du eine Email mit einem Termin bearbeitest, gehe wiefolgt vor: 1: Email lesen, 2: Termin extrahieren, 3: Kalender abrufen und schauen ob Termin noch frei, 4: Termin erstellen wenn frei, 5: Antwortmail senden"  # noqa: E501