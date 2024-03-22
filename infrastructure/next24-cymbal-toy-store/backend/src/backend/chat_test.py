import connector
import chat_handler
import logging
import os
import sys


logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s','%m-%d %H:%M:%S')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

secret_id = os.environ["DB_USER_SECRET_ID"]
project_id = os.environ["GCP_PROJECT"]  
db_password = connector.get_secret(secret_id, project_id)

instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]  # e.g. 'project:region:instance'
db_name = os.environ["DB_NAME"]  # e.g. 'my-database'
db_user = os.environ["DB_USER"]  # e.g. 'my-db-user'
db_connection = connector.connect_with_connector(instance_connection_name, db_name, db_user, db_password, False)
chat_be = chat_handler.ChatHandler(db_connection)

input1 = """[{"role":"user","text":"hi"}]"""
print(chat_be.respond(input1))

input2 = """[{"role":"user","text":"hi"}, {"role":"assistant","text":"Hi there! What can I help you with today"}, {"role":"user","text":"I'm looking for a birthday gift for a 6 year old girl who likes science."}]"""
print(chat_be.respond(input2))


