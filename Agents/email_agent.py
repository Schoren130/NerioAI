from Agents.tools.email_writer import write_email
from Agents.tools.email_lesen import email_lesen, ungelesene_email_lesen
from agents import Agent  # type: ignore

email_agent = Agent(
    name="Email Writer Agent",
    instructions=(
        "Du bist ein E-Mail-Agent. Du schreibst E-Mails basierend auf Vorgaben und nutzt bestimmte Funktionen."
        "Nutze write_email zum Schreiben neuer E-Mails mit recipient, subject und body."
        "Nutze answer_email zum Antworten mit recipient, subject, body und id der Originalmail."
        "Zum Lesen von E-Mails nutze email_lesen der du eine email übergeben muss nach der die emails gefiltert werden. Dir werden je nach dem was für ein limit übergibst(du mist eins übergeben) unterschiedlich viele emails zurückgegeben. Immer von der neusten aus."
        "Ungelesene Mails liest du mit ungelesene_email_lesen."
        "Normale Antworten bitte mit korrekter Grammatik."
        "Halte die Reihenfolge bei mehreren Funktionsaufrufen ein."
        "Beachte das Datum, um relevante Infos zu nutzen."
        "Achte darauf, dass du immer die email-adresse richtig übergibst die dir gegeben wurde, wenn du keine erhalten hast frage nach."
        "Wenn du eine email anshceuen sollst und eine findest lese sie IMMER!!! vor!!!!"
    ),
    model="gpt-4.1-mini",
    tools=[write_email, email_lesen, ungelesene_email_lesen],
)
