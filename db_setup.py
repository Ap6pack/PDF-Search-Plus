import sqlite3

# Database setup
def create_database(db_name="pdf_data.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER,
            page_number INTEGER,
            text TEXT,
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER,
            page_number INTEGER,
            image_name TEXT,
            image_ext TEXT,
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER,
            page_number INTEGER,
            keyword TEXT,
            context TEXT,
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database and tables created successfully.")

# Run the function to create the database and tables
if __name__ == "__main__":
    create_database()
