# GraphCart

**A polyglot-persistence product recommender over Amazon reviews, combining MySQL, MongoDB and Neo4j.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-relational-4479A1?logo=mysql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-documents-47A248?logo=mongodb&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-graph-4581C3?logo=neo4j&logoColor=white)

GraphCart loads Amazon product reviews from several categories into three different databases, each chosen for what it does best. On top of them it builds an analytics dashboard, a popularity-based recommender, and user-similarity graphs.

> Final project for the *Databases* course, Universidad Pontificia Comillas (ICAI).

---

## Architecture

```
            Amazon reviews (JSON lines, 5-core)
                          │
                   load_data.py  ── batched ETL (5,000 rows per batch)
            ┌─────────────┴──────────────┐
            ▼                            ▼
      MySQL (relational)           MongoDB (documents)
  REVIEWER_NAME, PRODUCT_CATEGORY,  review text, summary,
  REVIEW (ratings, dates, FKs)      helpfulness votes
            │                            │
            ├── recomendacion.py         │
            ├── menu_visualizacion.py ◄──┘
            ▼
      neo4JProyecto.py ──► Neo4j (graph)
      user–user similarity, user–product, user–category, shared-items graphs
```

| Store | What it holds | Why |
|---|---|---|
| **MySQL** | Normalised reviewers, products and ratings with primary/foreign keys | Structured aggregations and joins (popularity, distributions, time series) |
| **MongoDB** | Free-text review body and summary, linked by `reviewID` | Flexible, text-heavy documents for word clouds and text mining |
| **Neo4j** | Users, products and categories as nodes, with weighted relationships | Natural model for similarity networks and shared-taste exploration |

## Features

- **ETL pipeline**: streams JSON-lines files, parses dates, and inserts into MySQL and MongoDB in batches (`INSERT IGNORE` for deduplication). `insert_dataset.py` adds a new category incrementally.
- **Recommender** (`recomendacion.py`): for a given user and category, returns the 10 most-reviewed products the user has not reviewed yet.
- **Interactive dashboard** (`menu_visualizacion.py`, Rich + Matplotlib/Seaborn):
  reviews per year · product popularity curve · rating histograms by category or product · cumulative reviews over time · reviews-per-user distribution · word clouds from MongoDB summaries · per-user usage of any word (combining MongoDB text with MySQL authorship).
- **Graph analytics** (`neo4JProyecto.py`):
  - **Pearson-correlation similarity** between the most active users, loaded as bidirectional `IS_SIMILAR` edges. The app then finds the user with the most neighbours.
  - Random-product subgraphs with `REVIEWED` edges carrying rating and timestamp.
  - Users active in several categories, linked to `CATEGORY` nodes with item counts.
  - Popular-product communities with `SHARES_ITEMS` edges weighted by the number of items in common.

## Getting started

**Requirements:** Python 3.10+, and local MySQL, MongoDB and Neo4j servers.

```bash
git clone https://github.com/javmartineez/GraphCart.git
cd GraphCart
pip install -r requirements.txt
```

1. Download the 5-core review files for *Toys and Games*, *Video Games*, *Digital Music* and *Musical Instruments* (and optionally *Sports and Outdoors*) from the [Amazon Review Data](https://cseweb.ucsd.edu/~jmcauley/datasets/amazon/links.html) collection and place them in `data/`.
2. Set your connection settings in `configuracion.py` (MySQL / MongoDB) and the Neo4j URI and credentials in `neo4JProyecto.py`.
3. Run the components:

```bash
python load_data.py            # create the schema and load all the data
python insert_dataset.py       # (optional) add the Sports and Outdoors category
python menu_visualizacion.py   # analytics dashboard
python recomendacion.py        # product recommendations for a user
python neo4JProyecto.py        # build and explore the Neo4j graphs
```

## Project structure

```
GraphCart/
├── configuracion.py        # Connection settings and data file paths
├── load_data.py            # Connections, MySQL schema and batched ETL
├── insert_dataset.py       # Incremental load of a new category
├── menu_visualizacion.py   # Interactive analytics dashboard
├── recomendacion.py        # Popularity-based recommender
├── neo4JProyecto.py        # Graph construction and queries in Neo4j
└── requirements.txt
```

## Tech stack

Python · MySQL (PyMySQL) · MongoDB (PyMongo) · Neo4j (Cypher) · pandas · Matplotlib · Seaborn · WordCloud · Rich

## Author

**Javier Martínez Berenguer** · [GitHub](https://github.com/javmartineez)
