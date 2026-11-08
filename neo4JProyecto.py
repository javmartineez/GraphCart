"Javier Martínez Berenguer"

from neo4j import GraphDatabase
import configuracion as conf 
import load_data as db 
import math
import os
import random
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel


console = Console()

# Neo4j connection settings are read from environment variables (never hard-code credentials)
uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
driver = GraphDatabase.driver(uri, auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "")))

def limpiar_base_datos():
    """
    Deletes all current nodes and relationships to start from scratch.
    """
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def obtener_n_usuarios_max_reviews(cursor, n:int) -> list:
    """
    Gets the n users with the most reviews

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - n (int): number of users to retrieve
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
    Computes the similarity of each of the users passed as
    argument with respect to the others.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - user_ids(list): list of the top N users with the most reviews.
        - limite_comparar(int): optional cap on the number of users to load
                                into Neo4j, regardless of how many users are passed
                                as argument.

    Returns:
        - similitudes(list[tuple]): list of tuples [(u_i, u_j, similarity)] for every pair
                                    of users
    """

    if limite_comparar: 
        user_ids = user_ids[:limite_comparar]
    
    # Get each user's rating for each item
    format_strings = ','.join(['%s'] * len(user_ids))
    sql = f"""
        SELECT reviewerID, asin, overall 
        FROM review 
        WHERE reviewerID IN ({format_strings})
    """
    cursor.execute(sql, tuple(user_ids))
    ratings_raw = cursor.fetchall()

    # Organise the data in a dictionary: { user_id: { asin: rating } }
    user_ratings = {}
    for uid, asin, rating in ratings_raw:
        if uid not in user_ratings:
            user_ratings[uid] = {}
        user_ratings[uid][asin] = rating

    user_means = {uid: sum(ratings.values()) / len(ratings) 
                  for uid, ratings in user_ratings.items()}

    # Compute pairwise similarities
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
    Loads the user pairs and the similarities between them
    into Neo4j.

    Args:
        - similitudes(list[tuple]): list of tuples [(u_i, u_j, similarity)] for every pair
                                    of users
    """

    with driver.session() as session:
            
            for u1, u2, sim in similitudes:

                #it must be a bidirectional relationship
                consulta = """
                        MERGE (u1:USER {id: $id_user1})
                        MERGE (u2:USER {id: $id_user2})
                        
                        MERGE (u1)-[r1:IS_SIMILAR]->(u2)
                        SET r1.similarity = $similarity
                        
                        MERGE (u2)-[r2:IS_SIMILAR]->(u1)
                        SET r2.similarity = $similarity
                    """
                session.run(consulta, id_user1=u1, id_user2=u2, similarity=sim)

    print("Users and similarities loaded.")


def obtener_user_max_vecinos():
    """
    Neo4j query to get the user with the largest number
    of neighbours in the similarity graph.
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
    
        print(f"The user with the most neighbours is: {res[0]}")


def obtener_articulos_aleatorios(cursor, categoria:str, n:int) -> list:
    """
    Selects n random items from a specific
    category and extracts every review associated with them.
    Retrieves the user id, the item, the review rating and the timestamp,
    to later build the graph in Neo4j

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the SQL statements.
        - categoria (str): product type [juguetes, videojuegos, musica, instrumentos].
        - n (int): number of items to pick at random.

    Returns:
        - reviews (list[tuple]): list of tuples where each tuple holds the review data
                                 (reviewerID, asin, overall, unixReviewTime) for
                                 the selected random items. Returns an empty list on error.
    """

    try:
        # Get every asin of the category requested by the user
        sql_asin = """
                    SELECT asin 
                    FROM product_category
                    WHERE category = %s
                """
        cursor.execute(sql_asin, (categoria,))
        todos_articulos = [art[0] for art in cursor.fetchall()]

        cantidad = min(n, len(todos_articulos))
        seleccionados = random.sample(todos_articulos, cantidad)

        # Fetch the reviews of the selected items
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
        print(f"Error getting random items: {e}")
        return []


def cargar_reviews_articulos(reviews:list[tuple]):
    """
    Loads the user and item nodes into Neo4j, creating a
    (REVIEWED) relationship between them. The relationship stores as properties
    the rating given by the user and the time of the review.

    Args:
        - reviews (list[tuple]): list of tuples obtained from the SQL database
                                 in the format (reviewerID, asin, overall, unixReviewTime).
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
        
        print(f"{len(reviews)} reviews processed.")

    except Exception as e:
        print(f"Error loading into Neo4j: {e}")


def obtener_usuarios_multi_categoria(cursor) -> dict:

    """
    Gets the first 400 users sorted alphabetically by name
    and keeps only those who have rated items of at least
    two different types. Also returns the number of items consumed
    of each type.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the SQL statements.

    Returns:
        - dict: nested dictionary with the users that meet the condition.
                Structure: {reviewerID: {category: count, ...}}
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

    # Query to get the counts per user and category
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

    # Keep the users with > 1 category
    usuarios_filtrados = {uid: cats for uid, cats in data.items() if len(cats) > 1}

    return usuarios_filtrados


def cargar_usuarios_categorias(datos_usuarios:dict):
    """
    Loads into Neo4j the nodes for the users and the product
    categories. Creates a (REVIEWED) relationship between user and category,
    storing as a property the number of items consumed of that type.

    Args:
        - datos_usuarios (dict): dictionary with the structure
                                 {reviewerID: {category: amount, ...}} containing
                                 the users who have rated more than one category.
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

        print(f"{len(datos_usuarios)} users loaded into Neo4j.")

    except Exception as e:
        print(f"Error loading categories into Neo4j: {e}")


def obtener_articulos_populares(cursor) -> tuple:

    """
    Gets the 5 most popular items with fewer than 40 reviews,
    together with every user who has rated them. It also computes
    how many items these users have rated in common across the whole
    database.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the SQL statements.

    Returns:
        - tuple: a tuple holding two lists:
            1. rel_up (list[tuple]): list of tuples (reviewerID, asin) linking the
                                     users to the 5 selected items.
            2. rel_uu (list[tuple]): list of tuples (reviewerID_1, reviewerID_2, common)
                                     with the number of items in common between pairs
                                     of users.
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
    Loads into Neo4j the most popular items (<40 reviews) and the users who
    rated them. It also creates affinity relationships (SHARES_ITEMS) directly
    between those users, indicating how many items they have in common in the whole DB.

    Args:
        - rel_up (list[tuple]): list of tuples (reviewerID, asin) linking the
                                users to the 5 most popular items.
        - rel_uu (list[tuple]): list of tuples (reviewerID_1, reviewerID_2, common)
                                with the number of items two users have in common.
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

    print(f"Loaded {len(rel_up)} user-product links and {len(rel_uu)} affinity links.")


def apartado_1(cursor):
    """
    Entry point for section 4.1.
    Gets the n users with the most reviews, computes the similarities
    (Pearson correlation) between every pair of users, loads these bidirectional
    relationships into Neo4j and shows the user with the most neighbours in the graph.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the SQL statements.
    """

    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    n_usuarios = 30
    user_ids = obtener_n_usuarios_max_reviews(cursor, n_usuarios)
    similitudes = calcular_similitudes_pearson(cursor, user_ids)

    cargar_usuarios(similitudes)
    console.print("[bold green]Load finished. You can now query the data in Neo4j.[/bold green]")
    obtener_user_max_vecinos()


def apartado_2(cursor):
    """
    Entry point for section 4.2.
    Asks the user in the terminal for a category and a number of random
    items. Extracts those items from SQL together with the users who
    rated them and loads them into Neo4j, storing the review rating and date
    as properties of the link.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the SQL statements.
    """

    categorias = ["juguetes", "videojuegos", "musica", "instrumentos"]
    categoria_user = Prompt.ask("Enter a category: ", choices=categorias, default="juguetes")
    n_articulos = int(input("Enter the number of random items: "))

    resultados_sql = obtener_articulos_aleatorios(cursor, categoria_user, n_articulos)

    if resultados_sql:
        cargar_reviews_articulos(resultados_sql)


def apartado_3(cursor):
    """
    Entry point for section 4.3.
    Selects the first 400 users sorted alphabetically and keeps
    only those who have rated items of more than one different
    category. Loads the user and item-type nodes into Neo4j, adding
    a property with the number of items consumed of that type.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the SQL statements.
    """

    datos_usuarios = obtener_usuarios_multi_categoria(cursor)
    cargar_usuarios_categorias(datos_usuarios)


def apartado_4(cursor):
    """
    Entry point for section 4.4.
    Extracts the 5 most popular items with fewer than 40 reviews and the users
    who rated them. Loads the consumption relationships (user-item) into Neo4j
    and creates links between the users themselves with the number of
    items they have in common across the whole database.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the SQL statements.
    """
    rel_up, rel_uu = obtener_articulos_populares(cursor)
    cargar_populares_comunes(rel_up, rel_uu)

def mostrar_menu() -> str:
    """
    Menu showing the options using the Rich library.

    Returns:
        - str: option chosen from those shown in the menu
    """
    texto_menu = """
                [1] User similarities (section 4.1)
                [2] Links between users and random items (section 4.2)
                [3] Multi-category users (section 4.3)
                [4] Popular items and items in common (section 4.4)
                [0] Quit
                    """
    console.print(Panel(texto_menu, title="[bold cyan]Neo4j menu - Databases project[/bold cyan]", expand=False))

    opcion = Prompt.ask(
        "[bold yellow]Select an option[/bold yellow]",
        choices=["0", "1", "2", "3", "4", "5"], 
        default="0"
    )
    return opcion

def main():
    """
    Main entry point of the program.
    Handles the database connections and the interactive menu loop.
    """
    # Connect to MySQL
    try:
        conn_sql = db.get_sql_connection()
        cursor = conn_sql.cursor()
        cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")
        console.print("[bold green]Connected to MySQL successfully.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error connecting to MySQL: {e}[/bold red]")
        return

    
    try:
        while True:
            console.print("\n")
            opcion = mostrar_menu()
            limpiar_base_datos()

            if opcion == "1":
                console.print("\n[bold magenta]--- Running section 4.1 ---[/bold magenta]")
                apartado_1(cursor)
                
            elif opcion == "2":
                console.print("\n[bold magenta]--- Running section 4.2 ---[/bold magenta]") 
                apartado_2(cursor)
                console.print("[bold green]Load finished. You can now query the data in Neo4j.[/bold green]")
                
            elif opcion == "3":
                console.print("\n[bold magenta]--- Running section 4.3 ---[/bold magenta]")
                apartado_3(cursor)
                console.print("[bold green]Load finished. You can now query the data in Neo4j.[/bold green]")
                
            elif opcion == "4":
                console.print("\n[bold magenta]--- Running section 4.4 ---[/bold magenta]")
                apartado_4(cursor)
                console.print("[bold green]Load finished. You can now query the data in Neo4j.[/bold green]")
                
            elif opcion == "0":
                console.print("\n[bold blue]See you soon![/bold blue]")
                break

    except KeyboardInterrupt:
        console.print("\n[bold red]Execution interrupted by the user.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red] An unexpected error occurred: {e}[/bold red]")
    finally:
        cursor.close()
        conn_sql.close()
        driver.close()


if __name__ == "__main__":
    main()

 