"Javier Martínez Berenguer"

from neo4j import GraphDatabase
import configuracion as conf 
import load_data as db 
import math
import random
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel


console = Console()

uri = "neo4j://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "YOUR_NEO4J_PASSWORD"))

def limpiar_base_datos():
    """
    Borra todos los nodos y relaciones actuales para empezar desde cero.
    """
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def obtener_n_usuarios_max_reviews(cursor, n:int) -> list:
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


def calcular_similitudes_pearson(cursor, user_ids:list, limite_comparar=None) -> list[tuple]:

    """
    Función encargada de calcular las similitud de cada uno de los usuarios 
    enviados por argumento con respecto a los demás. 

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - user_ids(list): lista de top N usuarios con más reviews realizadas.
        - limite_comparar(int): variable para simplificar el numero de usuarios a cargar 
                                en neo4J independientemente del números de usuarios enviados
                                por argumento.

    Returns: 
        - similitudes(list[tuple]): lista de tuplas [(u_i, u_j, similitud)] para todos los pares 
                                    de usuarios
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


def cargar_usuarios(similitudes:list): 

    """
    Función para cargar los pares de usuarios y las similitudes entre ellos
    en neo4J.

    Args: 
        - similitudes(list[tuple]): lista de tuplas [(u_i, u_j, similitud)] para todos los pares 
                                    de usuarios
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
    """
    Función de consulta en Neo4J para obtener el usuario con mayor número 
    de vecinos en el grafo de similitudes. 
    """

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


def obtener_articulos_aleatorios(cursor, categoria:str, n:int) -> list:
    """
    Función encargada de seleccionar un número n de artículos aleatorios de una 
    categoría específica y extraer todas las reviews asociadas a dichos artículos. 
    Recupera el id del usuario, el artículo, la nota de la review y el timestamp,
    para posteriormente generar el grafo en Neo4J
    
    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo para ejecutar las sentencias SQL.
        - categoria (str): tipo de producto [juguetes, videojuegos, musica, instrumentos].
        - n (int): numero de artículos a escoger de forma aleatoria.
    
    Returns:
        - reviews (list[tuple]): Lista de tuplas donde cada tupla contiene los datos de la 
                                 review (reviewerID, asin, overall, unixReviewTime) correspondientes 
                                 a los artículos aleatorios seleccionados. Retorna lista vacía si hay error.
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
        reviews = cursor.fetchall()
        return reviews

    except Exception as e:
        print(f"Error al obtener artículos aleatorios: {e}")
        return []


def cargar_reviews_articulos(reviews:list[tuple]):
    """
    Carga en Neo4J los nodos de usuarios y artículos, estableciendo una 
    relación (REVIEWED) entre ellos. Dicha relación incluye como propiedades 
    la nota dada por el usuario y el momento de la review.

    Args: 
        - reviews (list[tuple]): Lista de tuplas obtenida de la base de datos 
                                 SQL con el formato (reviewerID, asin, overall, unixReviewTime).
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


def obtener_usuarios_multi_categoria(cursor) -> dict:

    """
    Obtiene los primeros 400 usuarios ordenados alfabéticamente por su nombre 
    y filtra exclusivamente aquellos que han puntuado artículos de, al menos, 
    dos tipos distintos. Retorna además la cantidad de artículos consumidos 
    por cada tipo.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo para ejecutar las sentencias SQL.

    Returns:
        - dict: Diccionario anidado con los usuarios que cumplen la condición. 
                Estructura: {reviewerID: {categoria: conteo, ...}}
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


def cargar_usuarios_categorias(datos_usuarios:dict):
    """
    Carga en Neo4J los nodos correspondientes a los usuarios y a las categorías 
    de productos. Crea una relación (REVIEWED) entre el usuario y la categoría, 
    almacenando como propiedad el número de artículos consumidos de dicho tipo.

    Args: 
        - datos_usuarios (dict): Diccionario con la estructura 
                                 {reviewerID: {categoria: cantidad, ...}} que contiene 
                                 los usuarios que han puntuado más de una categoría.
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


def obtener_articulos_populares(cursor) -> tuple:

    """
    Obtiene los 5 artículos más populares que tienen menos de 40 reviews, 
    junto con todos los usuarios que los han puntuado. Además, calcula la 
    cantidad de artículos que estos usuarios han puntuado en común en toda 
    la base de datos.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo para ejecutar las sentencias SQL.

    Returns:
        - tuple: Una tupla que contiene dos listas:
            1. rel_up (list[tuple]): Lista de tuplas (reviewerID, asin) que relaciona a los 
                                     usuarios con los 5 artículos seleccionados.
            2. rel_uu (list[tuple]): Lista de tuplas (reviewerID_1, reviewerID_2, comunes) 
                                     que indica el número de artículos en común entre pares 
                                     de usuarios.
    """

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

    format_strings = ','.join(['%s'] * len(top_5_asins))
    sql_users = f"""
        SELECT reviewerID, asin 
        FROM review 
        WHERE asin IN ({format_strings})
    """
    cursor.execute(sql_users, tuple(top_5_asins))
    rel_up = cursor.fetchall() # (user, asin)

    lista_usuarios = list(set([r[0] for r in rel_up]))
    
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
    rel_uu = cursor.fetchall() # (user1, user2, count)

    return rel_up, rel_uu


def cargar_populares_comunes(rel_up:list, rel_uu:list):
    """
    Carga en Neo4J los artículos más populares (<40 reviews) y los usuarios que 
    los han puntuado. Además, genera relaciones de afinidad (SHARES_ITEMS) directamente 
    entre dichos usuarios, indicando cuántos artículos tienen en común en toda la BBDD.

    Args: 
        - rel_up (list[tuple]): Lista de tuplas (reviewerID, asin) que relaciona a los 
                                usuarios con los 5 artículos más populares.
        - rel_uu (list[tuple]): Lista de tuplas (reviewerID_1, reviewerID_2, comunes) 
                                que indica la cantidad de artículos en común entre dos usuarios.
    """
    with driver.session() as session:

        consulta_up = """
            MERGE (u:USER {id: $uid})
            MERGE (p:PRODUCT {id: $asin})
            MERGE (u)-[:REVIEWED]->(p)
        """
        for uid, asin in rel_up:
            session.run(consulta_up, uid=uid, asin=asin)

        consulta_uu = """
            MATCH (u1:USER {id: $uid1})
            MATCH (u2:USER {id: $uid2})
            MERGE (u1)-[r:SHARES_ITEMS]-(u2)
            SET r.count = $count
        """
        for u1, u2, count in rel_uu:
            session.run(consulta_uu, uid1=u1, uid2=u2, count=count)

    print(f"Cargados {len(rel_up)} enlaces usuario-producto y {len(rel_uu)} enlaces de afinidad.")


def apartado_1(cursor):
    """
    Función principal de ejecución del apartado 4.1.
    Obtiene los n usuarios con mayor número de reviews, calcula las similitudes 
    (correlación de Pearson) entre cada par de usuarios, carga estas relaciones 
    bidireccionales en Neo4J y muestra el usuario con más vecinos en el grafo.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo para ejecutar las sentencias SQL.
    """

    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    n_usuarios = 30
    user_ids = obtener_n_usuarios_max_reviews(cursor, n_usuarios)
    similitudes = calcular_similitudes_pearson(cursor, user_ids)

    cargar_usuarios(similitudes)
    console.print("[bold green]Carga finalizada. Ya puedes consultar los datos en Neo4J.[/bold green]")
    obtener_user_max_vecinos()


def apartado_2(cursor):
    """
    Función principal de ejecución del apartado 4.2.
    Solicita al usuario por terminal una categoría y un número de artículos 
    aleatorios. Extrae de SQL dichos artículos junto con los usuarios que los 
    han puntuado y los carga en Neo4J, incluyendo como propiedades en el enlace 
    la nota y la fecha de la review.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo para ejecutar las sentencias SQL.
    """

    categorias = ["juguetes", "videojuegos", "musica", "instrumentos"]
    categoria_user = Prompt.ask("Introduce categoría: ", choices=categorias, default="juguetes")
    n_articulos = int(input("Introduce el número de articulos aleatorios: "))

    resultados_sql = obtener_articulos_aleatorios(cursor, categoria_user, n_articulos)

    if resultados_sql:
        cargar_reviews_articulos(resultados_sql)


def apartado_3(cursor):
    """
    Función principal de ejecución del apartado 4.3.
    Selecciona los 400 primeros usuarios ordenados alfabéticamente y filtra 
    exclusivamente a aquellos que han puntuado artículos de más de una categoría 
    distinta. Carga en Neo4J los nodos de usuarios y tipos de artículo, añadiendo 
    una propiedad con la cantidad de artículos consumidos de ese tipo.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo para ejecutar las sentencias SQL.
    """

    datos_usuarios = obtener_usuarios_multi_categoria(cursor)
    cargar_usuarios_categorias(datos_usuarios)


def apartado_4(cursor):
    """
    Función principal de ejecución del apartado 4.4.
    Extrae los 5 artículos más populares con menos de 40 reviews y los usuarios 
    que los han puntuado. Carga en Neo4J las relaciones de consumo (usuario-artículo) 
    y genera enlaces entre los propios usuarios indicando el número de 
    artículos que tienen en común en toda la base de datos.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo para ejecutar las sentencias SQL.
    """
    rel_up, rel_uu = obtener_articulos_populares(cursor)
    cargar_populares_comunes(rel_up, rel_uu)

def mostrar_menu() -> str:
    """
    Función de menú mostrando las opciones mediante la librería Rich.

    Returns: 
        - str: Opción a escoger de entre las mostradas en el menú
    """
    texto_menu = """
                [1] Obtener similitudes entre usuarios (Apartado 4.1)
                [2] Obtener enlaces entre usuarios y artículos aleatorios (Apartado 4.2)
                [3] Obtener usuarios multi-categoría (Apartado 4.3)
                [4] Artículos populares y artículos en común (Apartado 4.4)
                [0] Salir
                    """
    console.print(Panel(texto_menu, title="[bold cyan]Menú Neo4J - Proyecto BD[/bold cyan]", expand=False))
    
    opcion = Prompt.ask(
        "[bold yellow]Selecciona una opción[/bold yellow]", 
        choices=["0", "1", "2", "3", "4", "5"], 
        default="0"
    )
    return opcion

def main():
    """
    Función principal de ejecución del programa. 
    Gestiona la conexión a las bases de datos y el bucle del menú interactivo.
    """
    # Establecer conexión con MySQL
    try:
        conn_sql = db.get_sql_connection()
        cursor = conn_sql.cursor()
        cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")
        console.print("[bold green]Conexión a MySQL establecida correctamente.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error conectando a MySQL: {e}[/bold red]")
        return

    
    try:
        while True:
            console.print("\n")
            opcion = mostrar_menu()
            limpiar_base_datos()

            if opcion == "1":
                console.print("\n[bold magenta]--- Ejecutando Apartado 4.1 ---[/bold magenta]")
                apartado_1(cursor)
                
            elif opcion == "2":
                console.print("\n[bold magenta]--- Ejecutando Apartado 4.2 ---[/bold magenta]") 
                apartado_2(cursor)
                console.print("[bold green]Carga finalizada. Ya puedes consultar los datos en Neo4J.[/bold green]")
                
            elif opcion == "3":
                console.print("\n[bold magenta]--- Ejecutando Apartado 4.3 ---[/bold magenta]")
                apartado_3(cursor)
                console.print("[bold green]Carga finalizada. Ya puedes consultar los datos en Neo4J.[/bold green]")
                
            elif opcion == "4":
                console.print("\n[bold magenta]--- Ejecutando Apartado 4.4 ---[/bold magenta]")
                apartado_4(cursor)
                console.print("[bold green]Carga finalizada. Ya puedes consultar los datos en Neo4J.[/bold green]")
                
            elif opcion == "0":
                console.print("\n[bold blue]¡Hasta pronto![/bold blue]")
                break
                
    except KeyboardInterrupt:
        console.print("\n[bold red]Ejecución interrumpida por el usuario.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red] Ha ocurrido un error inesperado: {e}[/bold red]")
    finally:
        cursor.close()
        conn_sql.close()
        driver.close()


if __name__ == "__main__":
    main()

 