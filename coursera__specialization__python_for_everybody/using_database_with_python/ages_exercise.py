import sys
import sqlite3

connexion = sqlite3.connect("db.sqlite3")

cursor = connexion.cursor()

def setup():
    cursor.execute("""
        CREATE TABLE Ages ( 
            name VARCHAR(128), 
            age INTEGER
        )
    """)
    cursor.execute("DELETE FROM Ages")
    cursor.executemany("INSERT INTO Ages (name, age) VALUES (?, ?)", [
            ('Finan', 37),
            ('Mehik', 36),
            ('Salter', 36),
            ('Millicent', 39),
        ])
    connexion.commit()

def query():
    response = cursor.execute("SELECT hex(name || age) AS X FROM Ages ORDER BY X")
    print(response.fetchall())


if __name__ == "__main__":
    command = sys.argv[1]
    if command == 'setup':
        setup()
    elif command == 'query':
        query()

