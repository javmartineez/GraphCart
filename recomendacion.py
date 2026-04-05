"Javier Martinez Berenguer"

import load_data as db 
import configuracion as conf 
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def obtener_articulos(cursor, userid, categoria):
    """
    Función para obtener todos los artículos de la categoría 
    pedida que el usuario aún no ha consumido. 

    Args: 
        - userid (str): identificador del usuario
        - categoria (str): tipo de producto
    
    Returns:
        - list[str]: Lista con los asin de los artículos disponibles 
                     para recomendar al usuario (los aún no consumidos).
    """
    sql = """
            SELECT DISTINCT p.asin
            FROM product_category p
            WHERE p.category = %s
                AND p.asin NOT IN (SELECT r.asin
                                   FROM review r
                                   WHERE r.reviewerID = %s);
            """ 
    cursor.execute(sql, (categoria, userid))
    resultado = cursor.fetchall()

    return [art[0] for art in resultado]


def recomendar(cursor, userid, categoria):
    """
    Función que recibe un identificador de usuario y un tipo de 
    producto y devuelve los 10 artículos más populares
    que no ha consumido. La popularidad se mide en función del 
    número de reviews.

    Args: 
        - userid (str): identificador del usuario
        - categoria (str): tipo de producto
    """

    asins = obtener_articulos(cursor, userid, categoria)
    
    format_strings = ','.join(['%s'] * len(asins))
    
    sql = f"""
        SELECT asin, COUNT(reviewID) as popularidad
        FROM review
        WHERE asin IN ({format_strings})
        GROUP BY asin
        ORDER BY popularidad DESC
        LIMIT 10;
    """
    
    cursor.execute(sql, tuple(asins))
    resultados = cursor.fetchall()

    return resultados


def verificar_usuario(cursor, userid) -> bool:
    """
    Comprueba si el identificador de usuario existe en la base de datos MySQL.
    
    Returns:
        - bool: True si el usuario existe, False en caso contrario.
    """
    sql = """SELECT reviewerID 
             FROM reviewer_name WHERE reviewerID = %s 
             LIMIT 1;
        """
    
    cursor.execute(sql, (userid,))
    return cursor.fetchone() is not None 



def main():
    """
    Función principal de ejecución
    """

    console.print(Panel.fit(
        "[bold cyan]SISTEMA DE RECOMENDACIÓN [/bold cyan]\n[italic]Proyecto BBDD - Javier Martinez Berenguer[/italic]",
        border_style="blue"
    ))

    try:
        conn_sql = db.get_sql_connection()
        cursor = conn_sql.cursor()
        cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")
    except Exception as e:
        console.print(f"[bold red]Error de conexión:[/bold red] {e}")
        return

    userid = Prompt.ask("[bold yellow]Introduce tu ID de usuario[/bold yellow] (ej. A3V6Z4RCDGRC44)").strip()

    if not verificar_usuario(cursor, userid):
        console.print(f"\n[bold red]Error:[/bold red] El usuario [bold]{userid}[/bold] no existe.")
        cursor.close()
        conn_sql.close()
        return
    
    categoria = Prompt.ask(
        "[bold yellow]Selecciona una categoría[/bold yellow]", 
        choices=["juguetes", "videojuegos", "musica", "instrumentos"],
        default="juguetes"
    ).strip()

    console.print("[bold green]Buscando las mejores recomendaciones...[/bold green]")
    recomendaciones = recomendar(cursor, userid, categoria)
    console.print("\n")

    if recomendaciones:
        table = Table(title=f"Top 10 Recomendaciones para {userid}", title_style="bold magenta")
        table.add_column("Posición", justify="center", style="cyan", no_wrap=True)
        table.add_column("ASIN (Producto)", style="white")
        table.add_column("Popularidad (Reviews)", justify="right", style="green")

        for i, (asin, popularidad) in enumerate(recomendaciones, 1):
            table.add_row(str(i), asin, f"{popularidad:,}")

        console.print(table)
        console.print(f"\n Se han encontrado {len(recomendaciones)} productos ideales para este perfil.")
    else:
        console.print("No se han encontrado artículos nuevos para recomendar en esta categoría.")


    cursor.close()
    conn_sql.close()


if __name__ == "__main__":
    main()