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
    Función encargada de leer un nuevo fichero e insertarlo en la base de datos existente
    Args:
        - connection (pymysql.connections.Connection): Objeto de conexión para confirmar (commit) 
                                                   los cambios en el esquema.
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - collection_mongo (pymongo.collection): colección de documentos en MongoDB
    """

    batch_size = 5000
    
    # Obtener el ID máximo actual
    cursor_sql.execute("SELECT MAX(reviewID) FROM REVIEW")
    max_id = cursor_sql.fetchone()[0]
    review_id_counter = (max_id + 1) if max_id is not None else 1

    # Actualizamos nuevos datos en el fichero de configuración 
    conf.DATA_PATHS[CATEGORIA] = NEW_PATH
        
    batch_reviews = []
    batch_reviewers = []
    batch_products = []
    batch_mongo = []

    with open(NEW_PATH, 'r', encoding="utf-8") as f:
        for linea in f:
            data = json.loads(linea)

            # Procesar Fecha 
            fecha_dt = datetime.strptime(data['reviewTime'], '%m %d, %Y')
            fecha_sql = fecha_dt.strftime('%Y-%m-%d')

            # Preparar lotes para SQL
            batch_reviewers.append((data['reviewerID'], data.get('reviewerName', 'Unknown')))
            batch_products.append((data['asin'], CATEGORIA))
            batch_reviews.append((
                                review_id_counter, 
                                data['reviewerID'], 
                                data['asin'], 
                                data['overall'], 
                                fecha_sql, 
                                data['unixReviewTime']))

            # Preparar datos para MongoDB
            batch_mongo.append({
                                "reviewID": review_id_counter,
                                "category": CATEGORIA,
                                "reviewText": data.get('reviewText', ''),
                                "summary": data.get('summary', ''),
                                "helpful": data.get('helpful', [0, 0])
                            })

            review_id_counter += 1

            # Inserción por lotes cuando alcanzamos el batch_size
            if len(batch_reviews) >= batch_size:
                execute_batch(cursor_sql, collection_mongo, 
                                batch_reviewers, batch_products, batch_reviews, batch_mongo)
                # Limpiar listas para el siguiente lote
                batch_reviewers, batch_products, batch_reviews, batch_mongo = [], [], [], []

        # Insertar los restos que queden al final del archivo
        if batch_reviews:
            execute_batch(cursor_sql, collection_mongo, 
                            batch_reviewers, batch_products, batch_reviews, batch_mongo)

    connection_sql.commit()
    print("Carga de datos finalizada.")


def execute_batch(cursor, col_mongo, reviewers, products, reviews, mongo_docs):
    """
    Función auxiliar para ejecutar los inserts de un lote
    """
    
    cursor.executemany("INSERT IGNORE INTO REVIEWER_NAME(reviewerID, reviewerName) VALUES (%s, %s)", reviewers)
    cursor.executemany("INSERT IGNORE INTO PRODUCT_CATEGORY(asin, category) VALUES (%s, %s)", products)
    cursor.executemany("INSERT INTO REVIEW(reviewID, reviewerID, asin, overall, reviewTime, unixReviewTime) VALUES (%s, %s, %s, %s, %s, %s)", reviews)
    
    col_mongo.insert_many(mongo_docs)



def main():
    """
    Función principal de ejecución
    """

    conn_sql = db.get_sql_connection()
    cursor = conn_sql.cursor()

    mongo_col = db.get_mongo_connection()

    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    insert_data(conn_sql, cursor, mongo_col)


if __name__ == "__main__":
    main()