"Javier Martínez Berenguer"

import configuracion as conf 
import pymysql 
import pymongo
import json
from datetime import datetime


#Preguntas por FORMA NORMAL REVIEWTIME, UNIXREVIEWTIME !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def get_sql_connection():
    """
    Función de conexión con MySQL
    
    Returns: 
            - connection_sql (obj)
    """
    try: 
        connection_sql =pymysql.connect(host=conf.MYSQL_CONFIG["host"],
                                    user=conf.MYSQL_CONFIG["user"],
                                    password=conf.MYSQL_CONFIG["password"])
        return connection_sql

    except pymysql.MySQLError as e: 
        print("Error al conectar con MySQL: ", e)
        return None


def get_mongo_connection():
    """
    Función de conexión con MONGODB
    
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
        print("Error al conectar con MongoDB: ", e)
        return None
    

def create_sql_database(connection:pymysql.connections.Connection, cursor: pymysql.cursors.Cursor):

    """
    Crea la estructura de la base de datos en MySQL y sus tablas relacionadas
    y define las claves primarias y foráneas para asegurar la integridad
    referencial de los datos.

    Args:
        connection (pymysql.connections.Connection): Objeto de conexión para confirmar (commit) 
                                                   los cambios en el esquema.
        cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
    """
    
    db_name = conf.MYSQL_CONFIG["database"]

    sql = f"CREATE DATABASE IF NOT EXISTS {db_name}"
    cursor.execute(sql)

    sql = f"USE {db_name}"
    cursor.execute(sql)

    # 1. Tabla REVIEWER_NAME
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS REVIEWER_NAME(
            reviewerID VARCHAR(255) PRIMARY KEY,
            reviewerName Text
        )
    """)

    # 2. Tabla PRODUCT
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PRODUCT_CATEGORY(
            asin VARCHAR(255) PRIMARY KEY,
            category TEXT
        )
    """)

    # 3. Tabla REVIEWS
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


def insert_data(connection_sql:pymysql.connections.Connection, cursor_sql:pymysql.connections.Connection, 
                collection_mongo:pymongo.collection):
    """
    Función encargada de leer los ficheros, procesar los datos e insertalos por lotes.
    Args:
        - connection (pymysql.connections.Connection): Objeto de conexión para confirmar (commit) 
                                                   los cambios en el esquema.
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - collection_mongo (pymongo.collection): colección de documentos en MongoDB
    """

    batch_size = 5000
    review_id_counter = 1

    for categoria, ruta in conf.DATA_PATHS.items():
        print(f"Procesando categoría: {categoria}...")
        
        batch_reviews = []
        batch_reviewers = []
        batch_products = []
        batch_mongo = []

        with open(ruta, 'r', encoding="utf-8") as f:
            for linea in f:
                data = json.loads(linea)

                # Procesar Fecha 
                fecha_dt = datetime.strptime(data['reviewTime'], '%m %d, %Y')
                fecha_sql = fecha_dt.strftime('%Y-%m-%d')

                # Preparar lotes para SQL
                batch_reviewers.append((data['reviewerID'], data.get('reviewerName', 'Unknown')))
                batch_products.append((data['asin'], categoria))
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
                                    "category": categoria,
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



if __name__ == "__main__":
    
    sql_conn = get_sql_connection()
    mongo_col = get_mongo_connection()

    if sql_conn is not None and mongo_col is not None:
        try:
            cursor = sql_conn.cursor()
            
            create_sql_database(sql_conn, cursor)
            insert_data(sql_conn, cursor, mongo_col)
            
        except Exception as e:
            print(f"Ocurrió un error durante la ejecución: {e}")
        finally:
            cursor.close()
            sql_conn.close()
    else:
        print("No se pudo establecer la conexión con las bases de datos.")