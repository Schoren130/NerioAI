from Agents.calendar_agent import calendar_agent
from Agents.email_agent import email_agent
from Agents.tools.helpers.timefunction import get_time
from agents import Agent  # type: ignore
from Agents.tools.commands import send_command

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
    ),
    model="gpt-4.1-mini",
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
        send_command
    ]
)
