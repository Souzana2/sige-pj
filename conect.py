import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",   # coloca a tua senha se tiver
        database="sige_db"
    )
print ("Conexão com a base de dados estabelecida com sucesso!")