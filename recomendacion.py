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
    Gets every item of the requested category
    that the user has not consumed yet.

    Args:
        - userid (str): user identifier
        - categoria (str): product type

    Returns:
        - list[str]: list with the asin of the items available
                     to recommend to the user (those not consumed yet).
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
    Receives a user identifier and a product type
    and returns the 10 most popular items
    the user has not consumed. Popularity is measured by the
    number of reviews.

    Args:
        - userid (str): user identifier
        - categoria (str): product type
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
    Checks whether the user identifier exists in the MySQL database.

    Returns:
        - bool: True if the user exists, False otherwise.
    """
    sql = """SELECT reviewerID 
             FROM reviewer_name WHERE reviewerID = %s 
             LIMIT 1;
        """
    
    cursor.execute(sql, (userid,))
    return cursor.fetchone() is not None 



def main():
    """
    Main entry point
    """

    console.print(Panel.fit(
        "[bold cyan]RECOMMENDATION SYSTEM [/bold cyan]\n[italic]Databases project - Javier Martinez Berenguer[/italic]",
        border_style="blue"
    ))

    try:
        conn_sql = db.get_sql_connection()
        cursor = conn_sql.cursor()
        cursor.execute(f"USE {conf.MYSQL_CONFIG['database']}")
    except Exception as e:
        console.print(f"[bold red]Connection error:[/bold red] {e}")
        return

    userid = Prompt.ask("[bold yellow]Enter your user ID[/bold yellow] (e.g. A3V6Z4RCDGRC44)").strip()

    if not verificar_usuario(cursor, userid):
        console.print(f"\n[bold red]Error:[/bold red] User [bold]{userid}[/bold] does not exist.")
        cursor.close()
        conn_sql.close()
        return
    
    categoria = Prompt.ask(
        "[bold yellow]Select a category[/bold yellow]", 
        choices=["juguetes", "videojuegos", "musica", "instrumentos"],
        default="juguetes"
    ).strip()

    console.print("[bold green]Looking for the best recommendations...[/bold green]")
    recomendaciones = recomendar(cursor, userid, categoria)
    console.print("\n")

    if recomendaciones:
        table = Table(title=f"Top 10 recommendations for {userid}", title_style="bold magenta")
        table.add_column("Rank", justify="center", style="cyan", no_wrap=True)
        table.add_column("ASIN (Product)", style="white")
        table.add_column("Popularity (reviews)", justify="right", style="green")

        for i, (asin, popularidad) in enumerate(recomendaciones, 1):
            table.add_row(str(i), asin, f"{popularidad:,}")

        console.print(table)
        console.print(f"\n Found {len(recomendaciones)} ideal products for this profile.")
    else:
        console.print("No new items to recommend were found in this category.")


    cursor.close()
    conn_sql.close()


if __name__ == "__main__":
    main()