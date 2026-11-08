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
    Bar chart with the number of reviews written per year
    from 1998 to 2014, optionally filtered by category.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - categoria (str): product category, 'todo' (all) by default
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
            console.print(f"No data for category: {categoria}")
            return

        df = pd.DataFrame(resultados, columns=['Year', 'Number of reviews'])
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df, x='Year', y='Number of reviews', color='blue')
        plt.title(f"Reviews per year - {categoria}")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red] Error:[/bold red] {e}")
        


def plot_popularidad(cursor, categoria="todo"):

    """
    Item popularity plot based on the number of
    reviews written for each item, optionally filtered
    by category.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - categoria (str): product category, 'todo' (all) by default
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
            console.print(f"[bold red] No data for category: {categoria}[/bold red]")
            return

        df = pd.DataFrame(resultados, columns=["Item", 'Number of reviews'])
        df['Ranking'] = range(1, len(df) + 1)

        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='Ranking', y='Number of reviews', color='blue')
        plt.title(f"Item popularity - {categoria}")
        plt.xlabel("Items")
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_histograma_nota(cursor, categoria="todo", asin=None):

    """
    Bar chart with the number of reviews for each possible rating
    (1-5), by category, by individual item or for everything together.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - categoria (str): product category, 'todo' (all) by default
        - asin (str): item id to filter by, None by default
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
            titulo = f"Rating distribution for item {asin}"

        elif categoria.lower() == "todo":
            sql = """
                SELECT overall, COUNT(*) as frecuencia 
                FROM REVIEW 
                GROUP BY overall 
                ORDER BY overall
            """
            params = None
            titulo = "Rating distribution: all categories"
            
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
            titulo = f"Rating distribution - {categoria}"

        cursor.execute(sql, params)
        resultados = cursor.fetchall()

        if not resultados:
            if asin:
                console.print(f"Error: item {asin} does not exist.")
            else:
                console.print(f"Error: no data for category {categoria}.")
            return

        df = pd.DataFrame(resultados, columns=['nota', 'frecuencia'])

        plt.figure(figsize=(10, 6))
        sns.barplot(data=df, x='nota', y='frecuencia', color='blue')

        plt.title(titulo, fontsize=14)
        plt.xlabel("Rating (Overall)")
        plt.ylabel("Number of reviews")
        
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_evolucion_temporal(cursor, categoria="todo"):

    """
    Plot of the evolution of reviews over time, based on the cumulative
    number of reviews up to each date, optionally filtered
    by category.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - categoria (str): product category, 'todo' (all) by default
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
            print(f"No data found for category: {categoria}")
            return


        df = pd.DataFrame(resultados, columns=['timestamp', 'num_reviews'])
        df['reviews_acumuladas'] = df['num_reviews'].cumsum()

        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='timestamp', y='reviews_acumuladas', color='blue')

        plt.title(f"Cumulative reviews over time: {categoria}")
        plt.xlabel("Time (Unix timestamp)")
        plt.ylabel("Cumulative number of reviews")
        
        plt.tight_layout()
        plt.show()
    
    except pymysql.MySQLError as e:
        console.print(f"[bold red]SQL query error:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_reviews_usuario(cursor):

    """
    Histogram of the number of reviews written per user.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
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
            print("Not enough data to generate this chart.")
            return

        df = pd.DataFrame(resultados, columns=['Usuario', 'Num_Reviews'])

        plt.figure(figsize=(10, 6))
        sns.histplot(df['Num_Reviews'], bins=100, kde=False, color='blue')

        plt.title("Distribution of reviews per user")
        plt.xlabel("Number of reviews")
        plt.ylabel("Number of users")

        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_nube_palabras(coleccion_mongo, categoria):

    """
    Word cloud generated from the summary field for words
    longer than 3 letters. The size of each word in the chart
    is determined by how often it appears. It cannot be
    generated for all categories together.

    Args:
        - coleccion_mongo (pymongo.collection): 'Reviews' document collection
        - categoria (str): product category.
    """

    
    if categoria.lower() == "todo" or categoria not in conf.DATA_PATHS.keys():
        print("Error: invalid category.")
        print(f"Available categories: {list(conf.DATA_PATHS.keys())}")
        return

    print(f"Generating word cloud for category: {categoria}...")

    try:
        cursor_mongo = coleccion_mongo.find(
                                            {"category": categoria}, 
                                            {"summary": 1, "_id": 0}
                                        )

        # Join all the summaries into a single string
        texto_completo = ""
        for doc in cursor_mongo:
            summary = doc.get('summary', '')
            if summary:
                texto_completo += " " + str(summary)

        if not texto_completo.strip():
            print(f"Not enough words to generate the cloud for {categoria}.")
            return

        #length filter > 3 characters
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
        plt.title(f"Most frequent words in {categoria} reviews")
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def plot_usuarios_word_custom(cursor, coleccion_mongo, word:str):
    """
    Histogram of how many times each user has written the word entered
    in the console across all their historical reviews.

    Args:
        - cursor (pymysql.cursors.Cursor): active cursor used to run the statements
        - coleccion_mongo (pymongo.collection): 'Reviews' document collection
        - word (str): word to analyse
    """
    print(f"Counting how many times each user has used the word '{word}'...")
    
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
            print(f"No mentions of the word '{word}' were found")
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
        plt.title(f"Use of the word '{word.upper()}' per user")
        plt.xlabel(f"Times the user has used the word {word}")
        plt.ylabel("Number of users (log scale)")
        
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")



def mostrar_menu():

    """
    Menu showing the visualisation options using
    the Rich library.

    Returns:
        - Prompt: option chosen from those shown in the menu
    """
  
    console.print(Panel.fit(
        "[bold cyan]Amazon Reviews - Visualisation Dashboard[/bold cyan]\n"
        "[italic white]Databases Project - ICAI - Javier Martínez Berenguer[/italic white]",
        border_style="green"
    ))

    tabla = Table(show_header=True, header_style="bold magenta", expand=True)
    tabla.add_column("Option", style="dim", width=6, justify="center")
    tabla.add_column("Description")

    tabla.add_row("1", "Reviews per year")
    tabla.add_row("2", "Item popularity")
    tabla.add_row("3", "Histogram of reviews by rating")
    tabla.add_row("4", "Reviews over time")
    tabla.add_row("5", "Distribution of reviews per user")
    tabla.add_row("6", "Word cloud by category")
    tabla.add_row("7", "Word usage per user (free section)")
    tabla.add_row("8", "[bold red]Quit[/bold red]")

    console.print(tabla)
    
    return Prompt.ask("Select an option", choices=[str(i) for i in range(1, 9)])



def main():
    """
    Main entry point.
    """

    sql_conn = db.get_sql_connection()
    mongo_col = db.get_mongo_connection()
    
    if not sql_conn or mongo_col is None:
        console.print("[bold red]Error: could not connect to the databases.[/bold red]")
        return

    cursor = sql_conn.cursor()
    cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")

    categorias_validas = list(conf.DATA_PATHS.keys()) + ["todo"]

    while True:
        opcion = mostrar_menu()

        # 1: Reviews per year
        if opcion == "1":
            cat = Prompt.ask("Filter by category (ENTER to include all)", choices=categorias_validas, default="todo")
            plot_reviews_por_año(cursor, cat)
            
        # 2: Popularity
        elif opcion == "2":
            cat = Prompt.ask("Filter by category (ENTER to include all)", choices=categorias_validas, default="todo")
            plot_popularidad(cursor, cat)

        # 3: Histogram by rating
        elif opcion == "3":
            console.print("\n[bold cyan]Histogram filter:[/bold cyan]")
            tipo = Prompt.ask("Filter by individual (a)rticle or (c)ategory?", choices=["a", "c"], default="c")

            if tipo == "a":
                asin_input = Prompt.ask("Enter the item ASIN")
                plot_histograma_nota(cursor, asin=asin_input)
            else:
                cat_input = Prompt.ask("Filter by category (ENTER to include all)", choices=categorias_validas, default="todo")
                plot_histograma_nota(cursor, categoria=cat_input)

        # 4: Cumulative evolution
        elif opcion == "4":
            cat = Prompt.ask("Filter by category (ENTER to include all)", choices=categorias_validas, default="todo")
            plot_evolucion_temporal(cursor, cat)

        # 5: Reviews per user
        elif opcion == "5":
            plot_reviews_usuario(cursor)

        # 6: Word cloud (Mongo)
        elif opcion == "6":
            cat = Prompt.ask("Enter a specific category", default="juguetes")
            plot_nube_palabras(mongo_col, cat)
            
        # 7: Custom word
        elif opcion == "7":
            word = Prompt.ask("Which word do you want to analyse?")
            plot_usuarios_word_custom(cursor, mongo_col, word)
            
        elif opcion == "8":
            console.print("[bold yellow]See you soon![/bold yellow]")
            break
        
        console.print("\n" + "—" * 60 + "\n")



if __name__ == "__main__":
    main()