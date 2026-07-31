import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()

hostname=os.getenv('PSQL_HOST_NAME')
database=os.getenv('PSQL_DATABASE')
username=os.getenv('PSQL_USERNAME')
password=os.getenv('PSQL_PASSWORD')
port_id=os.getenv('PSQL_PORT_ID')

conn=None
cur=None

try:
    conn=psycopg2.connect(host=hostname,dbname=database,user=username,password=password,port=port_id)
    cur=conn.cursor()

    create_user_table=""" CREATE TABLE IF NOT EXISTS user_table (id int PRIMARY KEY,
    name varchar(50),
    age int,
    email varchar(255),
    phone_number varchar(20),
    created_at timestamptz,
    updated_at timestamptz,
    status varchar(10))"""
    
    cur.execute(create_user_table)

    conn.commit()
    

except Exception as e:
    print(e)
finally:
    if cur is not None:
        cur.close()
    if conn is not None:
        conn.close()