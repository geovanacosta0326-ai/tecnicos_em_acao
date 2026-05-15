import psycopg2

conn = psycopg2.connect(
    host="177.22.38.27",
    port="6432",
    database="painel_ateg",
    user="postgres",
    password="ranes%2015"
)

print("CONECTADO")