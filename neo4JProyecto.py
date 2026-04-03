from neo4j import GraphDatabase
import configuracion as conf 
import load_data as db 
import math
import random
from rich.console import Console
from rich.prompt import Prompt


console = Console()

uri = "neo4j://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "YOUR_NEO4J_PASSWORD"))

def limpiar_base_datos():
    """
    Borra todos los nodos y relaciones actuales para empezar desde cero.
    """
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def obtener_n_usuarios(cursor, n:int):
    """
    Función para obtener los n usuarios con más reviews realizadas 

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - n (int): número de usuarios a recuperar
    """

    sql = """
        SELECT reviewerID
        FROM review
        GROUP BY reviewerID 
        ORDER BY COUNT(reviewID) DESC 
        LIMIT %s;
    """

    cursor.execute(sql, (n,))
    tupla_users = cursor.fetchall()

    return [u[0] for u in tupla_users]


def calcular_similitudes_pearson(cursor, user_ids, limite_comparar=None):
    """
    Calcula la correlación de Pearson entre n usuarios basándose en sus ratings.
    Retorna una lista de tuplas (user1, user2, similitud)
    """
    if limite_comparar: 
        user_ids = user_ids[:limite_comparar]
    
    # Obtener las valoraciones de cada usuario para cada articulo
    format_strings = ','.join(['%s'] * len(user_ids))
    sql = f"""
        SELECT reviewerID, asin, overall 
        FROM review 
        WHERE reviewerID IN ({format_strings})
    """
    cursor.execute(sql, tuple(user_ids))
    ratings_raw = cursor.fetchall()

    # Organizamos los datos en un diccionario: { user_id: { asin: rating } }
    user_ratings = {}
    for uid, asin, rating in ratings_raw:
        if uid not in user_ratings:
            user_ratings[uid] = {}
        user_ratings[uid][asin] = rating

    user_means = {uid: sum(ratings.values()) / len(ratings) 
                  for uid, ratings in user_ratings.items()}

    # Calcular las similitudes por pares
    similitudes = []
    n = len(user_ids)
    
    for i in range(n):
        for j in range(i + 1, n):
            u = user_ids[i]
            v = user_ids[j]
            
            comunes = set(user_ratings[u].keys()) & set(user_ratings[v].keys())
            
            if len(comunes) > 0:
                numerador = 0
                suma_sq_u = 0
                suma_sq_v = 0
                
                for item in comunes:
                    diff_u = user_ratings[u][item] - user_means[u]
                    diff_v = user_ratings[v][item] - user_means[v]
                    
                    numerador += diff_u * diff_v
                    suma_sq_u += diff_u ** 2
                    suma_sq_v += diff_v ** 2
                
                denominador = math.sqrt(suma_sq_u) * math.sqrt(suma_sq_v)
                
                if denominador != 0:
                    similitud = numerador / denominador
                    similitudes.append((u, v, similitud))

    return similitudes


def load_users(similitudes:list): 
    """
    Función para cargar los pares de usuarios y las similitudes entre ellos
    en neo4J.

    Args: 
        - similitudes (list): lista de tuplas de similitudes para cada par de
                              usuarios: (user1, user2, similitud)
    """
    with driver.session() as session:
            
            for u1, u2, sim in similitudes:

                #debe ser una relacion bidireccional
                consulta = """
                        MERGE (u1:USER {id: $id_user1})
                        MERGE (u2:USER {id: $id_user2})
                        
                        MERGE (u1)-[r1:IS_SIMILAR]->(u2)
                        SET r1.similarity = $similarity
                        
                        MERGE (u2)-[r2:IS_SIMILAR]->(u1)
                        SET r2.similarity = $similarity
                    """
                session.run(consulta, id_user1=u1, id_user2=u2, similarity=sim)

    print("Usuarios y similitudes cargadas.")


def obtener_user_max_vecinos():

    with driver.session() as session:
        consulta = """
            MATCH (u1:USER) -[s:IS_SIMILAR]-> (u2:USER)
            WITH u1, COUNT(s) AS num_vecinos
            RETURN u1 
            ORDER BY num_vecinos 
            LIMIT 1
            """

        resultado = session.run(consulta)
        res = resultado.data()
    
        print(f"El usuario con más vecinos es: {res[0]}")


def articulos_aleatorios(cursor, categoria: str, n: int):
    """
    Selecciona n artículos aleatorios de una categoría y recupera sus reviews.
    """
    try:
        # Obtenemos todos los asin de la categoría pedida por el usuario
        sql_asin = """
                    SELECT asin 
                    FROM product_category
                    WHERE category = %s
                """
        cursor.execute(sql_asin, (categoria,))
        todos_articulos = [art[0] for art in cursor.fetchall()]

        cantidad = min(n, len(todos_articulos))
        seleccionados = random.sample(todos_articulos, cantidad)

        # Buscamos las reviews de los articulos seleccionados
        format_strings = ','.join(['%s'] * len(seleccionados))
        sql_reviews = f"""
            SELECT reviewerID, asin, overall, unixReviewTime 
            FROM review 
            WHERE asin IN ({format_strings})
        """
        cursor.execute(sql_reviews, tuple(seleccionados))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error al obtener artículos aleatorios: {e}")
        return []


def load_random_reviews(reviews):
    """
    Carga reviews en Neo4j usando un bucle for tradicional.
    """

    consulta = """
    MERGE (u:USER {id: $uid})
    MERGE (p:PRODUCT {id: $asin})
    MERGE (u)-[r:REVIEWED]->(p)
    SET r.rating = $rating,
        r.timestamp = $time
    """

    try:
        with driver.session() as session:
            for row in reviews:
       
                uid =row[0]
                asin = row[1]
                rating = float(row[2])
                time = int(row[3])

                session.run(consulta, uid=uid, asin=asin, rating=rating, time=time)
        
        print(f"Se han procesado {len(reviews)} reviews.")
        
    except Exception as e:
        print(f"Error cargando en Neo4j: {e}")



def obtener_usuarios_multi_categoria(cursor):
    """
    Filtra los usuarios que han puntuado más de una categoría distinta.
    Retorna un diccionario: { reviewerID: { categoria: conteo, ... } }
    """
    sql_400 = """
        SELECT reviewerID 
        FROM reviewer_name
        ORDER BY reviewerName 
        LIMIT 400;
        """
    
    cursor.execute(sql_400)
    resultado = cursor.fetchall()

    users_raw = [uid[0] for uid in resultado]

    # Consulta para obtener los conteos por usuario y categoría
    format_strings = ','.join(['%s'] * len(users_raw))
    sql = f"""
        SELECT r.reviewerID, p.category, COUNT(r.asin) as num_articulos
        FROM review r
        INNER JOIN product_category p ON r.asin = p.asin
        WHERE r.reviewerID IN ({format_strings})
        GROUP BY r.reviewerID, p.category
    """
    cursor.execute(sql, tuple(users_raw))
    resultados = cursor.fetchall()

    data = {}
    for uid, cat, conteo in resultados:
        if uid not in data:
            data[uid] = {}
        data[uid][cat] = conteo

    # Nos quedamos con usuarios que tengan > 1 categoría
    usuarios_filtrados = {uid: cats for uid, cats in data.items() if len(cats) > 1}

    return usuarios_filtrados


def load_user_categories(datos_usuarios):
    """
    Carga en Neo4j la relación entre usuarios y categorías.
    """
    consulta = """
            MERGE (u:USER {id: $uid})
            MERGE (c:CATEGORY {name: $cat_name})
            MERGE (u)-[r:REVIEWED]->(c)
            SET r.count = $cantidad
            """

    try:
        with driver.session() as session:
            for uid, categorias in datos_usuarios.items():
                for cat_name, cantidad in categorias.items():
                    session.run(consulta, uid=uid, cat_name=cat_name, cantidad=cantidad)

        print(f"Se han cargado {len(datos_usuarios)} usuarios en Neo4j.")

    except Exception as e:
        print(f"Error cargando categorías en Neo4j: {e}")




def obtener_datos_seccion_4_4(cursor):
    """
    Obtiene los 5 artículos populares (<40 reviews), sus usuarios,
    y los artículos en común entre dichos usuarios.
    """
    # 1. Obtener los 5 ASINs
    sql_top_5 = """
        SELECT asin, COUNT(reviewID) as num_reviews
        FROM review 
        GROUP BY asin 
        HAVING num_reviews < 40
        ORDER BY num_reviews DESC
        LIMIT 5;
    """
    cursor.execute(sql_top_5)
    top_5_asins = [row[0] for row in cursor.fetchall()]

    # 2. Obtener todos los usuarios que han puntuado ESOS 5 artículos
    format_strings = ','.join(['%s'] * len(top_5_asins))
    sql_users = f"""
        SELECT reviewerID, asin 
        FROM review 
        WHERE asin IN ({format_strings})
    """
    cursor.execute(sql_users, tuple(top_5_asins))
    relaciones_up = cursor.fetchall() # (user, asin)

    # 3. Calcular artículos en común entre estos usuarios específicos
    # Extraemos la lista única de usuarios involucrados
    lista_usuarios = list(set([r[0] for r in relaciones_up]))
    
    # Buscamos cuántos artículos (en total de la DB) comparten
    format_users = ','.join(['%s'] * len(lista_usuarios))
    sql_comunes = f"""
        SELECT r1.reviewerID, r2.reviewerID, COUNT(r1.asin) as comunes
        FROM review r1
        JOIN review r2 ON r1.asin = r2.asin
        WHERE r1.reviewerID IN ({format_users}) 
          AND r2.reviewerID IN ({format_users})
          AND r1.reviewerID < r2.reviewerID
        GROUP BY r1.reviewerID, r2.reviewerID
    """
    cursor.execute(sql_comunes, tuple(lista_usuarios) * 2)
    relaciones_uu = cursor.fetchall() # (user1, user2, count)

    return relaciones_up, relaciones_uu


def load_popular_and_common(rel_up, rel_uu):
    """
    Carga los 5 artículos, sus usuarios y los enlaces de artículos comunes.
    """
    with driver.session() as session:
        # A. Cargar relaciones Usuario -> Producto
        consulta_up = """
            MERGE (u:USER {id: $uid})
            MERGE (p:PRODUCT {id: $asin})
            MERGE (u)-[:REVIEWED]->(p)
        """
        for uid, asin in rel_up:
            session.run(consulta_up, uid=uid, asin=asin)

        # B. Cargar relaciones Usuario <-> Usuario (Artículos comunes)
        consulta_uu = """
            MATCH (u1:USER {id: $uid1})
            MATCH (u2:USER {id: $uid2})
            MERGE (u1)-[r:SHARES_ITEMS]-(u2)
            SET r.count = $count
        """
        for u1, u2, count in rel_uu:
            session.run(consulta_uu, uid1=u1, uid2=u2, count=count)

    print(f"Cargados {len(rel_up)} enlaces usuario-producto y {len(rel_uu)} enlaces de afinidad.")



def main_pt1(cursor):
    """
    Función principal de ejecución del apartado 4.1.
    Cargamos en la base de datos los n_usuarios con mayor numero de 
    reviews y calculamos las similitudes entre cada para de 
    """

    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    n_usuarios = 30
    user_ids = obtener_n_usuarios(cursor, n_usuarios)
    similitudes = calcular_similitudes_pearson(cursor, user_ids)

    load_users(similitudes)
    obtener_user_max_vecinos()


def main_pt2(cursor):
    categorias = ["juguetes", "videojuegos", "musica", "instrumentos"]
    categoria_user = Prompt.ask("Introduce categoría: ", choices=categorias, default="juguetes")
    n_articulos = int(input("Introduce el número de articulos aleatorios: "))

    # Paso 1: Ir a SQL
    resultados_sql = articulos_aleatorios(cursor, categoria_user, n_articulos)

    # Paso 2: Mandar a Neo4j
    if resultados_sql:
        load_random_reviews(resultados_sql)


def main_pt3(cursor):
    datos_usuarios = obtener_usuarios_multi_categoria(cursor)
    load_user_categories(datos_usuarios)


def main_pt4(cursor):
    rel_up, rel_uu = obtener_datos_seccion_4_4(cursor)
    load_popular_and_common(rel_up, rel_uu)


if __name__ == "__main__":
    conn_sql = db.get_sql_connection()
    cursor = conn_sql.cursor()
    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    # limpiar_base_datos()
    # main_pt1(cursor)
    # limpiar_base_datos()
    # main_pt2(cursor)
    # limpiar_base_datos()
    # main_pt3(cursor)
    limpiar_base_datos()
    main_pt4(cursor)