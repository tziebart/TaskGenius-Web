import psycopg2

try:
    connection = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='GfjYpfc03onizwZU',
        host='db.yoboblatndnmcxvkzblc.supabase.co',
        port='5432',
        sslmode='require'
    )
    print("Connection successful")
except Exception as e:
    print(f"Error: {e}")