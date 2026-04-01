"Javier Martínez Berenguer"


# Credenciales y conexión MySQL
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "", #TODO
    "database": "AmazonReviewsDB" 
}

# Credenciales y conexión MongoDB
MONGO_CONFIG = {
    "host": "localhost",
    "port": 27017,
    "database": "AmazonReviewsDB", 
    "collection": "reviews"  
}

# Rutas de los archivos
DATA_PATHS = {
    "juguetes": "data/Toys_and_Games_5.json",
    "videojuegos": "data/Video_Games_5.json",
    "musica": "data/Digital_Music_5.json",
    "instrumentos": "data/Musical_Instruments_5.json",
}