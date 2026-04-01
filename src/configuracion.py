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
    "toys_games": "data/Toys_and_Games_5.json",
    "video_games": "data/Video_Games_5.json",
    "digital_music": "data/Digital_Music_5.json",
    "musical_instruments": "data/Musical_Instruments_5.json",
}