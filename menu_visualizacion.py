"Javier Martínez Berenguer"

import load_data as db
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
# from wordcloud import WordCloud

def plot_reviews_por_año(cursor, categoria="todo"):
    """Opción 1: Histograma de reviews por año"""
    
    if categoria.lower() == "todo":
        sql = """
            SELECT YEAR(reviewTime) AS anio, COUNT(reviewID) AS num_reviews
            FROM review 
            GROUP BY anio
            ORDER BY anio;
        """
        params = None
    else: 
        sql = """
            SELECT YEAR(reviewTime) AS anio, COUNT(reviewID) AS num_reviews
            FROM review r
            INNER JOIN product_category p on r.asin = p.asin
            WHERE p.category = %s
            GROUP BY anio
            ORDER BY anio;
        """
        params = (categoria,)

    cursor.execute(sql, params)
    resultados = cursor.fetchall()

    if not resultados:
        print(f"No se encontraron datos para la categoría: {categoria}")
        return

    df = pd.DataFrame(resultados, columns=['Año', 'Número de reviews'])

    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x='Año', y='Número de reviews', color='steelblue')

    plt.title(f"Reviews por año de la categoría:{categoria}")
    plt.xlabel("Año")
    plt.ylabel("Número de reviews")
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.show()
    

def plot_popularidad(cursor, categoria="todo"):
    """Opción 2: Curva de popularidad de artículos [cite: 90, 92]"""

    if categoria.lower() == "todo":
        sql = """
            SELECT asin, COUNT(reviewID) AS num_reviews 
            FROM review 
            GROUP BY asin
            ORDER BY num_reviews DESC; 
        """
        params = None
    else: 
        sql = """
            SELECT asin, COUNT(reviewID) AS num_reviews 
            FROM review r
            INNER JOIN product_category p on r.asin = p.asin
            WHERE p.category = %s
            GROUP BY asin
            ORDER BY num_reviews DESC; 
        """
        params = (categoria,)
    
    cursor.execute(sql, params)
    resultados = cursor.fetchall()

    if not resultados:
        print(f"No se encontraron datos para la categoría: {categoria}")
        return

    df = pd.DataFrame(resultados, columns=['Año', 'Número de reviews'])

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x='Año', y='Número de reviews', color='steelblue')

    plt.title(f"Reviews por año de la categoría:{categoria}")
    plt.xlabel("Año")
    plt.ylabel("Número de reviews")
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.show()

def plot_histograma_nota(cursor, categoria="todo", asin=None):
    """Opción 3: Histograma por nota (overall) [cite: 115, 127]"""
    # Si asin no es None, buscar artículo específico [cite: 127]
    # Si no existe, indicar que no existe 
    pass

def plot_nube_palabras(coleccion, categoria):
    """Opción 6: Nube de palabras (MongoDB) [cite: 174, 176]"""
    # Solo campo 'summary' 
    # Palabras longitud > 3 [cite: 175]
    # No se permite para "todas" las categorías [cite: 174]
    pass

def mostrar_menu():
    # """Imprime las opciones disponibles [cite: 72]"""
    # print("\n--- MENÚ DE VISUALIZACIÓN ---")
    # print("1. Evolución de reviews por años")
    # print("2. Evolución de popularidad")
    # print("3. Histograma por nota")
    # # ... resto de opciones [cite: 136, 150, 185]
    # print("8. Salir")
    # return input("Seleccione una opción: ")
    pass

def main():

    sql_conn = db.get_sql_connection()
    cursor = sql_conn.cursor()
    mongo_col = db.get_mongo_connection()
    
    opcion = ""
    while opcion != "8":
        opcion = mostrar_menu()
        
        if opcion == "1":
            cat = input("Introduce una categoría (juguetes, videojuegos, musica, instrumentos, todo): ")
            plot_reviews_por_año(cursor, cat)
        elif opcion == "2":
            cat = input("Introduce una categoría (juguetes, videojuegos, musica, instrumentos, todo): ")
            plot_popularidad(cursor, cat)
    pass


if __name__ == "__main__":

    conexion_sql = db.get_sql_connection()
    cursor = conexion_sql.cursor()

    plot_reviews_por_año(cursor, categoria="todo")