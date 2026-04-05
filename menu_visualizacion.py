"Javier Martínez Berenguer"

import load_data as db
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import pymysql
import configuracion as conf
import re
from wordcloud import WordCloud
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt



console = Console()


def plot_reviews_por_año(cursor, categoria="todo"):

    """
    Gráfico de barras con la evolución del número de reviews realizadas
    por año desde 1998 hasta 2014, con la opción de filtrar por categoría. 

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - categoria (str): categoría de producto, puesto a 'todo' como default
    """

    try:
        if categoria.lower() == "todo":
            sql = """
                SELECT YEAR(reviewTime) AS año, COUNT(reviewID) AS num_reviews
                FROM REVIEW 
                GROUP BY año
                ORDER BY año;
                """
            params = None
        else: 
            sql = """
                SELECT YEAR(r.reviewTime) AS anio, COUNT(r.reviewID) AS num_reviews
                FROM REVIEW r
                INNER JOIN product_category p on r.asin = p.asin
                WHERE p.category = %s
                GROUP BY anio
                ORDER BY anio;
            """
            params = (categoria,)

        cursor.execute(sql, params)
        resultados = cursor.fetchall()

        if not resultados:
            console.print(f"No hay datos para la categoría: {categoria}")
            return

        df = pd.DataFrame(resultados, columns=['Año', 'Número de reviews'])
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df, x='Año', y='Número de reviews', color='blue')
        plt.title(f"Reviews por año - {categoria}")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red] Error:[/bold red] {e}")
        


def plot_popularidad(cursor, categoria="todo"):

    """
    Plot de popularidad de articulos basada en el numero de 
    reviews creadas para cada artículo, con la opción de filtrar 
    por categoría. 

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - categoria (str): categoría de producto, puesto a 'todo' como default
    """

    try:
        if categoria.lower() == "todo":
            sql = """
                SELECT asin, COUNT(reviewID) AS num_reviews 
                FROM REVIEW 
                GROUP BY asin
                ORDER BY num_reviews DESC; 
            """
            params = None

        else: 
            sql = """
                SELECT r.asin, COUNT(r.reviewID) AS num_reviews 
                FROM REVIEW r
                INNER JOIN product_category p on r.asin = p.asin
                WHERE p.category = %s
                GROUP BY r.asin
                ORDER BY num_reviews DESC; 
            """
            params = (categoria,)
        
        cursor.execute(sql, params)
        resultados = cursor.fetchall()

        if not resultados:
            console.print(f"[bold red] No hay datos para la categoría: {categoria}[/bold red]")
            return

        df = pd.DataFrame(resultados, columns=["Artículo", 'Número de reviews'])
        df['Ranking'] = range(1, len(df) + 1)

        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='Ranking', y='Número de reviews', color='blue')
        plt.title(f"Popularidad de artículos - {categoria}")
        plt.xlabel("Artículos")
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_histograma_nota(cursor, categoria="todo", asin=None):

    """
    Diagrama de barras con el numero de reviews para cada posible valoración 
    (del 1-5), por categoría, por artículo individual o todo junto.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - categoria (str): categoría de producto, puesto a 'todo' como default
        - asin (str): id del articulo para filtrar, puesto a None como default
    """

    try:

        if asin is not None:
            sql = """
                SELECT overall, COUNT(*) as frecuencia 
                FROM REVIEW 
                WHERE asin = %s 
                GROUP BY overall 
                ORDER BY overall
            """
            params = (asin,)
            titulo = f"Distribución de notas para el artículo {asin}"

        elif categoria.lower() == "todo":
            sql = """
                SELECT overall, COUNT(*) as frecuencia 
                FROM REVIEW 
                GROUP BY overall 
                ORDER BY overall
            """
            params = None
            titulo = "Distribución de notas: Todas las categorías"
            
        else:
            sql = """
                SELECT r.overall, COUNT(*) as frecuencia 
                FROM REVIEW r
                INNER JOIN product_category p ON r.asin = p.asin
                WHERE p.category = %s
                GROUP BY r.overall
                ORDER BY r.overall
            """
            params = (categoria,)
            titulo = f"Distribución de notas - {categoria}"

        cursor.execute(sql, params)
        resultados = cursor.fetchall()

        if not resultados:
            if asin:
                console.print(f"Error:El artículo {asin} no existe.")
            else:
                console.print(f"Error: Sin datos para la categoría {categoria}.")
            return

        df = pd.DataFrame(resultados, columns=['nota', 'frecuencia'])

        plt.figure(figsize=(10, 6))
        sns.barplot(data=df, x='nota', y='frecuencia', color='blue')

        plt.title(titulo, fontsize=14)
        plt.xlabel("Valoración (Overall)")
        plt.ylabel("Número de Reviews")
        
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_evolucion_temporal(cursor, categoria="todo"):

    """
    Plot de la evolucion temporal de reviews basada en la suma del numero 
    total de reviews hasta una fecha concreta, con posibilidad de filtrar 
    por categoría. 

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - categoria (str): categoría de producto, puesto a 'todo' como default
    """
    
    try: 
        if categoria.lower() == "todo":
            sql = """
                SELECT unixReviewTime, COUNT(reviewID) as num_reviews
                FROM review 
                GROUP BY unixReviewTime
                ORDER BY unixReviewTime;
            """
            params = None

        else:
            sql = """
                SELECT r.unixReviewTime, COUNT(r.reviewID) as num_reviews
                FROM REVIEW r
                INNER JOIN product_category p ON r.asin = p.asin
                WHERE p.category = %s
                GROUP BY r.unixReviewTime
                ORDER BY r.unixReviewTime;
            """
            params = (categoria,)

        cursor.execute(sql, params)
        resultados = cursor.fetchall()

        if not resultados:
            print(f"No se encontraron datos para la categoría: {categoria}")
            return


        df = pd.DataFrame(resultados, columns=['timestamp', 'num_reviews'])
        df['reviews_acumuladas'] = df['num_reviews'].cumsum()

        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='timestamp', y='reviews_acumuladas', color='blue')

        plt.title(f"Evolución acumulada de reviews: {categoria}")
        plt.xlabel("Tiempo (Unix Timestamp)")
        plt.ylabel("Número acumulado de reviews")
        
        plt.tight_layout()
        plt.show()
    
    except pymysql.MySQLError as e:
        console.print(f"[bold red]Error en la consulta SQL:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_reviews_usuario(cursor):

    """
    Histograma del número de reviews generadas por usuario.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
    """

    try:
        sql = """
            SELECT reviewerID, COUNT(reviewID) as total_reviews
            FROM REVIEW
            GROUP BY reviewerID;
        """
        
        cursor.execute(sql)
        resultados = cursor.fetchall()

        if not resultados:
            print("No hay datos suficientes para generar esta gráfica.")
            return

        df = pd.DataFrame(resultados, columns=['Usuario', 'Num_Reviews'])

        plt.figure(figsize=(10, 6))
        sns.histplot(df['Num_Reviews'], bins=100, kde=False, color='blue')

        plt.title("Distribución de reviews por usuario")
        plt.xlabel("Número de reviews")
        plt.ylabel("Número de usuarios")

        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_nube_palabras(coleccion_mongo, categoria):

    """
    Nube de palabras generada a partir del campo summary para aquellas 
    palabras con una longitud superior a 3 letras. El tamaño de cada 
    palabra en el gráfico viene determinado por su prevalencia. No existe 
    posibilidad de filtrar por todas las categorías juntas.

    Args: 
        - coleccion_mongo (pymongo.collection): colección de documentos 'Reviews'
        - categoria (str): categoría del producto.
    """

    
    if categoria.lower() == "todo" or categoria not in conf.DATA_PATHS.keys():
        print("Error: categoría inválida.")
        print(f"Categorías disponibles: {list(conf.DATA_PATHS.keys())}")
        return

    print(f"Generando nube de palabras para la categoría: {categoria}...")

    try:
        cursor_mongo = coleccion_mongo.find(
                                            {"category": categoria}, 
                                            {"summary": 1, "_id": 0}
                                        )

        # Unimos todos los summaries en un solo string
        texto_completo = ""
        for doc in cursor_mongo:
            summary = doc.get('summary', '')
            if summary:
                texto_completo += " " + str(summary)

        if not texto_completo.strip():
            print(f"No hay palabras suficientes para generar la nube en {categoria}.")
            return

        #filtro de longitud > 3 caracteres
        palabras_filtradas = [word for word in texto_completo.split() if len(word) > 3]
        texto_final = " ".join(palabras_filtradas)

        wordcloud = WordCloud(
                                width=800, 
                                height=400,
                                background_color='white',
                                min_font_size=10
                            ).generate(texto_final)

        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.title(f"Palabras más frecuentes en reviews de {categoria}")
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_usuarios_word_custom(cursor, coleccion_mongo, word:str):
    """
    Histograma de la cantidad de veces que un usuario ha escrito la palabra indicada 
    por consola a lo largo de todas sus reviews históricamente.

    Args: 
        - cursor (pymysql.cursors.Cursor): Cursor activo ejecutar las sentencias
        - coleccion_mongo (pymongo.collection): colección de documentos 'Reviews'
        - word (str): palabra a analizar
    """
    print(f"Obteniendo el numero de veces que la palabra '{word}' ha sido utilizada por usuario...")
    
    try:
        cursor_mongo = coleccion_mongo.find(
                                            {}, 
                                            {"reviewID": 1, "reviewText": 1, "_id": 0}
                                        )
        
        counts_list = []
        for doc in cursor_mongo:
            texto = str(doc.get('reviewText', '')).lower()
            count = len(re.findall(fr'\b{word}\b', texto))
            
            if count > 0:
                counts_list.append({
                    'reviewID': doc['reviewID'], 
                    'word_count': count})

        if not counts_list:
            print(f"No se encontraron menciones de la palabra '{word}'")
            return

        df_mongo = pd.DataFrame(counts_list)

        sql = """
            SELECT reviewID, reviewerID 
            FROM review;
            """
        cursor.execute(sql)
        df_sql = pd.DataFrame(cursor.fetchall(), columns=['reviewID', 'reviewerID'])


        df_final = pd.merge(df_mongo, df_sql, on='reviewID')
        usuario_stats = df_final.groupby('reviewerID')['word_count'].sum().reset_index()


        plt.figure(figsize=(10, 6))
        sns.histplot(usuario_stats['word_count'], bins=15, color='blue', )

        plt.yscale('log') 
        plt.title(f"Uso de la palabra '{word.upper()}' por usuario")
        plt.xlabel(f"Veces que el usuario ha usado la palabra {word}")
        plt.ylabel("Número de usuarios (Escala Logarítmica)")
        
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def mostrar_menu():

    """
    Función de menú mostrando las opciones de visualización mediante 
    la librería Rich.

    Returns: 
        - Prompt: Opción a escoger de entre las mostradas en el menú
    """
  
    console.print(Panel.fit(
        "[bold cyan]Amazon Reviews - Dashboard de Visualización[/bold cyan]\n"
        "[italic white]Proyecto de Bases de Datos - ICAI - Javier Martínez Berenguer[/italic white]",
        border_style="green"
    ))

    tabla = Table(show_header=True, header_style="bold magenta", expand=True)
    tabla.add_column("Opción", style="dim", width=6, justify="center")
    tabla.add_column("Descripción")

    tabla.add_row("1", "Evolución de reviews por años")
    tabla.add_row("2", "Popularidad de artículos")
    tabla.add_row("3", "Histograma de reviews por nota")
    tabla.add_row("4", "Evolución temporal de reviews")
    tabla.add_row("5", "Distribución de reviews por usuario")
    tabla.add_row("6", "Nube de palabras por categoría")
    tabla.add_row("7", "Uso de palabras por usuario (Apartado Libre)")
    tabla.add_row("8", "[bold red]Salir[/bold red]")

    console.print(tabla)
    
    return Prompt.ask("Selecciona una opción", choices=[str(i) for i in range(1, 9)])



def main():
    """
    Función principal de ejecución.
    """

    sql_conn = db.get_sql_connection()
    mongo_col = db.get_mongo_connection()
    
    if not sql_conn or mongo_col is None:
        console.print("[bold red]Error: No se pudo conectar con las bases de datos.[/bold red]")
        return

    cursor = sql_conn.cursor()
    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    categorias_validas = list(conf.DATA_PATHS.keys()) + ["todo"]

    while True:
        opcion = mostrar_menu()

        # 1: Reviews por año
        if opcion == "1":
            cat = Prompt.ask("Filtra por una categoría (ENTER para incluir todas)", choices=categorias_validas, default="todo")
            plot_reviews_por_año(cursor, cat)
            
        # 2: Popularidad
        elif opcion == "2":
            cat = Prompt.ask("Filtra por una categoría (ENTER para incluir todas)", choices=categorias_validas, default="todo")
            plot_popularidad(cursor, cat)

        # 3: Histograma por nota
        elif opcion == "3":
            console.print("\n[bold cyan]Filtro de Histograma:[/bold cyan]")
            tipo = Prompt.ask("¿Filtrar por (a)rtículo individual o (c)ategoría?", choices=["a", "c"], default="c")
            
            if tipo == "a":
                asin_input = Prompt.ask("Introduce el ASIN del artículo")
                plot_histograma_nota(cursor, asin=asin_input)
            else:
                cat_input = Prompt.ask("Filtra por una categoría (ENTER para incluir todas)", choices=categorias_validas, default="todo")
                plot_histograma_nota(cursor, categoria=cat_input)

        # 4: Evolución acumulada
        elif opcion == "4":
            cat = Prompt.ask("Filtra por una categoría (ENTER para incluir todas)", choices=categorias_validas, default="todo")
            plot_evolucion_temporal(cursor, cat)

        # 5: Reviews por usuario
        elif opcion == "5":
            plot_reviews_usuario(cursor)

        # 6: Nube de palabras (Mongo)
        elif opcion == "6":
            cat = Prompt.ask("Introduce categoría específica", default="juguetes")
            plot_nube_palabras(mongo_col, cat)
            
        # 7: Palabra personalizada
        elif opcion == "7":
            word = Prompt.ask("¿Qué palabra quieres analizar?")
            plot_usuarios_word_custom(cursor, mongo_col, word)
            
        elif opcion == "8":
            console.print("[bold yellow]¡Hasta pronto![/bold yellow]")
            break
        
        console.print("\n" + "—" * 60 + "\n")



if __name__ == "__main__":
    main()