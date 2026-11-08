"Javier Martínez Berenguer"

import configuracion as conf 
import pymysql 
import pymongo
import json
from datetime import datetime


def get_sql_connection():
    """
    Opens a connection to MySQL
    
    Returns: 
            - connection_sql (obj)
    """
    try: 
        connection_sql =pymysql.connect(host=conf.MYSQL_CONFIG["host"],
                                    user=conf.MYSQL_CONFIG["user"],
                                    password=conf.MYSQL_CONFIG["password"])
        return connection_sql

    except pymysql.MySQLError as e: 
        print("Error connecting to MySQL: ", e)
        return None


def get_mongo_connection():
    """
    Opens a connection to MongoDB
    
    Returns: 
            - collection (obj)
    """
    try:
        MONGO_CONNECTION_STRING =f"mongodb://{conf.MONGO_CONFIG['host']}:{conf.MONGO_CONFIG['port']}" 
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        database = client[conf.MONGO_CONFIG["database"]]
        collection = database[conf.MONGO_CONFIG["collection"]]
        return collection
    
    except Exception as e: 
        print("Error connecting to MongoDB: ", e)
        return None
    

def create_sql_database(connection:pymysql.connections.Connection, cursor: pymysql.cursors.Cursor):

    """
    Creates the MySQL database structure and its related tables,
    defining primary and foreign keys to ensure the referential
    integrity of the data.

    Args:
        connection (pymysql.connections.Connection): connection object used to commit
                                                   the schema changes.
        cursor (pymysql.cursors.Cursor): active cursor used to run the statements
    """
    
    db_name = conf.MYSQL_CONFIG["database"]

    sql = f"CREATE DATABASE IF NOT EXISTS {db_name}"
    cursor.execute(sql)

    sql = f"USE {db_name}"
    cursor.execute(sql)

    # 1. REVIEWER_NAME table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS REVIEWER_NAME(
            reviewerID VARCHAR(255) PRIMARY KEY,
            reviewerName Text
        )
    """)

    # 2. PRODUCT table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PRODUCT_CATEGORY(
            asin VARCHAR(255) PRIMARY KEY,
            category TEXT
        )
    """)

    # 3. REVIEWS table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS REVIEW(
            reviewID BIGINT PRIMARY KEY,
            reviewerID VARCHAR(255),
            asin VARCHAR(255),
            overall REAL,
            reviewTime DATE,
            unixReviewTime BIGINT,
            FOREIGN KEY (reviewerID) REFERENCES REVIEWER_NAME(reviewerID),
            FOREIGN KEY (asin) REFERENCES PRODUCT_CATEGORY(asin)      
        )
    """)

    connection.commit()


def insert_data(connection_sql:pymysql.connections.Connection, cursor_sql:pymysql.cursors.Cursor, 
                collection_mongo:pymongo.collection):
    """
    Reads the files, processes the data and inserts it in batches.
    Args:
        - connection (pymysql.connections.Connection): connection object used to commit
                                                   the schema changes.
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - collection_mongo (pymongo.collection): MongoDB document collection
    """

    batch_size = 5000
    review_id_counter = 1

    for categoria, ruta in conf.DATA_PATHS.items():
        print(f"Processing category: {categoria}...")
        
        batch_reviews = []
        batch_reviewers = []
        batch_products = []
        batch_mongo = []

        with open(ruta, 'r', encoding="utf-8") as f:
            for linea in f:
                data = json.loads(linea)

                # Parse the date 
                fecha_dt = datetime.strptime(data['reviewTime'], '%m %d, %Y')
                fecha_sql = fecha_dt.strftime('%Y-%m-%d')

                # Prepare SQL batches
                batch_reviewers.append((data['reviewerID'], data.get('reviewerName', 'Unknown')))
                batch_products.append((data['asin'], categoria))
                batch_reviews.append((
                                    review_id_counter, 
                                    data['reviewerID'], 
                                    data['asin'], 
                                    data['overall'], 
                                    fecha_sql, 
                                    data['unixReviewTime']))

                # Prepare MongoDB data
                batch_mongo.append({
                                    "reviewID": review_id_counter,
                                    "category": categoria,
                                    "reviewText": data.get('reviewText', ''),
                                    "summary": data.get('summary', ''),
                                    "helpful": data.get('helpful', [0, 0])
                                })

                review_id_counter += 1

                # Insert a batch once batch_size is reached
                if len(batch_reviews) >= batch_size:
                    execute_batch(cursor_sql, collection_mongo, 
                                   batch_reviewers, batch_products, batch_reviews, batch_mongo)
                    # Clear the lists for the next batch
                    batch_reviewers, batch_products, batch_reviews, batch_mongo = [], [], [], []

            # Insert whatever is left at the end of the file
            if batch_reviews:
                execute_batch(cursor_sql, collection_mongo, 
                               batch_reviewers, batch_products, batch_reviews, batch_mongo)

    connection_sql.commit()
    print("Data load finished.")


def execute_batch(cursor, col_mongo, reviewers, products, reviews, mongo_docs):
    """
    Helper function that runs the inserts of a batch
    """
    
    cursor.executemany("INSERT IGNORE INTO REVIEWER_NAME(reviewerID, reviewerName) VALUES (%s, %s)", reviewers)
    cursor.executemany("INSERT IGNORE INTO PRODUCT_CATEGORY(asin, category) VALUES (%s, %s)", products)
    cursor.executemany("INSERT INTO REVIEW(reviewID, reviewerID, asin, overall, reviewTime, unixReviewTime) VALUES (%s, %s, %s, %s, %s, %s)", reviews)
    
    col_mongo.insert_many(mongo_docs)



if __name__ == "__main__":
    
    sql_conn = get_sql_connection()
    mongo_col = get_mongo_connection()

    if sql_conn is not None and mongo_col is not None:
        try:
            cursor = sql_conn.cursor()
            
            create_sql_database(sql_conn, cursor)
            insert_data(sql_conn, cursor, mongo_col)
            
        except Exception as e:
            print(f"An error occurred during execution: {e}")
        finally:
            cursor.close()
            sql_conn.close()
    else:
        print("Could not connect to the databases.")