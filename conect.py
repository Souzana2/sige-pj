import mysql.connector

DB_CONFIG = dict(
    host="localhost",
    user="root",
    password="",
    database="sige_db"
)

BASE_DB_CONFIG = {k: v for k, v in DB_CONFIG.items() if k != "database"}

DB_NAME = "sige_db"

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)