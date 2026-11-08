"Javier Martínez Berenguer"

import configuracion as conf 
import load_data as db
import pymysql
import pymongo
import json
from datetime import datetime


CATEGORIA = "deportes"
NEW_PATH = "data/Sports_and_Outdoors_5.json"

def insert_data(connection_sql:pymysql.connections.Connection, cursor_sql:pymysql.cursors.Cursor, 
                collection_mongo:pymongo.collection):
    """
    Reads a new file and inserts it into the existing database
    Args:
        - connection (pymysql.connections.Connection): connection object used to commit
                                                   the schema changes.
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - collection_mongo (pymongo.collection): MongoDB document collection
    """

    batch_size = 5000
    
    # Get the current maximum ID
    cursor_sql.execute("SELECT MAX(reviewID) FROM REVIEW")
    max_id = cursor_sql.fetchone()[0]
    review_id_counter = (max_id + 1) if max_id is not None else 1

    # Register the new data in the configuration 
    conf.DATA_PATHS[CATEGORIA] = NEW_PATH
        
    batch_reviews = []
    batch_reviewers = []
    batch_products = []
    batch_mongo = []

    with open(NEW_PATH, 'r', encoding="utf-8") as f:
        for linea in f:
            data = json.loads(linea)

            # Parse the date 
            fecha_dt = datetime.strptime(data['reviewTime'], '%m %d, %Y')
            fecha_sql = fecha_dt.strftime('%Y-%m-%d')

            # Prepare SQL batches
            batch_reviewers.append((data['reviewerID'], data.get('reviewerName', 'Unknown')))
            batch_products.append((data['asin'], CATEGORIA))
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
                                "category": CATEGORIA,
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



def main():
    """
    Main entry point
    """

    conn_sql = db.get_sql_connection()
    cursor = conn_sql.cursor()

    mongo_col = db.get_mongo_connection()

    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    insert_data(conn_sql, cursor, mongo_col)


if __name__ == "__main__":
    main()