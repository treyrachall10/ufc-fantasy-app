import psycopg2
import os

def get_db():
    '''
        Returns a connection and cursor to the database
    '''
    # Define connection parameters
    connection_params = {
        'dbname': os.environ.get('DB_NAME'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'host': os.environ.get('DB_HOST'),
        'port': os.environ.get('DB_PORT')
    }

    # Establishing the connection
    connection = psycopg2.connect(**connection_params)

    # Creating a cursor object
    cursor = connection.cursor()

    # Print connection status
    print("Connection to database established!")

    return connection, cursor
