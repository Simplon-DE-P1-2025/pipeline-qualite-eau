# api/main.py
# Point d'entrée FastAPI — Pipeline Qualité de l'Eau
# Connexion au SQL Warehouse Databricks via databricks-sql-connector

import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, HTTPException, Query
from databricks import sql
from typing import Optional


app = FastAPI(
    title="API Qualité de l'Eau",
    description="Exposition des tables Gold du pipeline qualité de l'eau distribuée en France",
    version="1.0.0"
)

# Connexion Databricks SQL Warehouse
def get_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"]
    )

# Endpoint racine
@app.get("/")
def root():
    return {
        "message": "API Qualité de l'Eau — Pipeline Databricks",
        "version": "1.0.0",
        "endpoints": [
            "/conformite_commune",
            "/evolution_parametres",
            "/carte_regions",
            "/top_communes",
            "/nonconformites"
        ]
    }

# Endpoint 1 — Conformité par commune
@app.get("/conformite_commune")
def conformite_commune(
    departement: Optional[str] = Query(None, description="Code département ex: 69"),
    limite: int = Query(100, description="Nombre de résultats")
):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = f"""
            SELECT * FROM workspace.gold.conformite_commune
            {'WHERE code_departement = ?' if departement else ''}
            LIMIT {limite}
        """
        params = [departement] if departement else []
        cursor.execute(query, params)
        colonnes = [col[0] for col in cursor.description]
        resultats = [dict(zip(colonnes, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"data": resultats, "count": len(resultats)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint 2 — Evolution des parametres
@app.get("/evolution_parametres")
def evolution_parametres(
    parametre: Optional[str] = Query(None, description="Code paramètre ex: NO3"),
    limite: int = Query(100, description="Nombre de résultats")
):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = f"""
            SELECT * FROM workspace.gold.evolution_parametres
            {'WHERE code_parametre = ?' if parametre else ''}
            ORDER BY annee, mois
            LIMIT {limite}
        """
        params = [parametre] if parametre else []
        cursor.execute(query, params)
        colonnes = [col[0] for col in cursor.description]
        resultats = [dict(zip(colonnes, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"data": resultats, "count": len(resultats)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint 3 — Carte regions
@app.get("/carte_regions")
def carte_regions():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workspace.gold.carte_regions ORDER BY code_departement")
        colonnes = [col[0] for col in cursor.description]
        resultats = [dict(zip(colonnes, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"data": resultats, "count": len(resultats)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint 4 — Top communes
# CORRECTION : ajout du parametre ordre (desc=top, asc=flop) pour afficher les deux classements
@app.get("/top_communes")
def top_communes(
    departement: Optional[str] = Query(None, description="Code département ex: 69"),
    limite: int = Query(10, description="Nombre de résultats"),
    ordre: str = Query("desc", description="Ordre de tri : desc (top) ou asc (flop)")
):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Validation de l'ordre pour éviter une injection SQL
        ordre_sql = "DESC" if ordre.lower() != "asc" else "ASC"
        query = f"""
            SELECT * FROM workspace.gold.top_communes
            {'WHERE code_departement = ?' if departement else ''}
            ORDER BY taux_conformite_pct {ordre_sql}
            LIMIT {limite}
        """
        params = [departement] if departement else []
        cursor.execute(query, params)
        colonnes = [col[0] for col in cursor.description]
        resultats = [dict(zip(colonnes, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"data": resultats, "count": len(resultats)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint 5 — Non-conformites
@app.get("/nonconformites")
def nonconformites(
    annee: Optional[int] = Query(None, description="Année ex: 2024"),
    limite: int = Query(100, description="Nombre de résultats")
):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = f"""
            SELECT * FROM workspace.gold.nonconformites
            {'WHERE annee = ?' if annee else ''}
            LIMIT {limite}
        """
        params = [annee] if annee else []
        cursor.execute(query, params)
        colonnes = [col[0] for col in cursor.description]
        resultats = [dict(zip(colonnes, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"data": resultats, "count": len(resultats)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))