import sys
import sqlite3

connexion = sqlite3.connect("db.sqlite3")

cursor = connexion.cursor()

def setup():
    cursor.execute("""
        CREATE TABLE users(
            name VARCHAR(128),
            email VARCHAR(128)
        )
    """)
    cursor.execute("""
        INSERT INTO users VALUES
        ('Angelito', 'angelito@test.com'),   
        ('Dan', 'dan@test.com')
    """)
    connexion.commit()

def query():
    response = cursor.execute("SELECT * FROM users")
    print(response.fetchall())


if __name__ == "__main__":
    command = sys.argv[1]
    if command == 'setup':
        setup()
    elif command == 'query':
        query()
