#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 17:46:15 2025

@author: andreadesogus
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import datetime
import json
import os

# Importa le classi dai moduli (assicurati che i file siano nella stessa cartella o correttamente importabili)
from msci_weight import MSCIWeightsExtractor, normalize_to_100, read_json_dictionary
from msci_price_data import MSCIIndexFetcher, index_dictionary
from black_litterman import BlackLitterman
from helper import fetch_index_data, fig_to_base64, get_msci_weight

app = Flask(__name__)
CORS(app)  # Abilita CORS per permettere le chiamate dal frontend Node.js

@app.route("/")
def home():
    return "Benvenuto nell'app Flask!"

@app.route("/api/", methods=["GET"])
def api_root():
    return jsonify({"message": "API attiva!"})

# ===============================================================
# Endpoint per MSCI Weights - Sector
# ===============================================================
@app.route("/api/weights/sector", methods=["GET"])
def get_sector_weights():
    weights = get_msci_weight()
    return jesonify(weights)


# ===============================================================
# Endpoint per MSCI Weights - Country
# ===============================================================
@app.route("/api/weights/country", methods=["GET"])
def get_country_weights():
    extractor = MSCIWeightsExtractor()
    country_dict = extractor.get_country_weights()
    return jsonify(country_dict)

# ===============================================================
# Endpoint per i dati storici dell'indice MSCI
# Le date vengono passate come parametri di query (es. ?start_date=2018-01-02&end_date=2025-02-17)
# ===============================================================
@app.route("/api/index/data", methods=["GET"])
def get_index_data():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if not start_date or not end_date:
        return jsonify({"error": "I parametri start_date e end_date sono obbligatori"}), 400
    try:
        res_dict = fetch_index_data(start_date, end_date)
        return jsonify(res_dict)
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

# ===============================================================
# Endpoint per il modello Black–Litterman
# Il client invia in POST un JSON con la composizione di mercato, il tasso di risk aversion, le view (opzionali)
# e i dati storici dei prezzi (price_data)
# ===============================================================
@app.route("/api/black-litterman/optimal-weights", methods=["POST"])
def compute_optimal_weights():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Il body della richiesta è vuoto"}), 400
        
        market_comp = get_msci_weight()
        risk_aversion = data.get("risk_aversion")
        max_deviation = data.get("max_deviation", 0.20)
        views = data.get("views", [])

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        if not start_date or not end_date:
            return jsonify({"error": "I parametri start_date e end_date sono obbligatori"}), 400

        # Otteniamo i dati storici MSCI basandoci sulle date scelte dall'utente
        price_data = fetch_index_data(start_date, end_date)  

        if not price_data:
            return jsonify({"error": "Nessun dato trovato per l'intervallo di date selezionato"}), 400

        price_df = pd.DataFrame(price_data)

        # Creiamo il modello Black-Litterman
        bl_model = BlackLitterman(market_composition=market_comp, price_data=price_df, risk_aversion=risk_aversion)
        
        if views:
            P, Q, Omega = bl_model.add_views(views)
            mu_post = bl_model.compute_posterior_returns(P, Q, Omega)
        else:
            mu_post = bl_model.compute_equilibrium_returns()

        optimal_weights = bl_model.compute_optimal_weights(mu_post, max_deviation=max_deviation)
        result = {asset: weight for asset, weight in zip(bl_model.assets, optimal_weights)}

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Vercel ha bisogno di questa riga:
def handler(event, context):
    return app(event, context)
# ===============================================================
# Main: esecuzione dell'app (Vercel utilizzerà direttamente 'app')
# ===============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Prendi la porta da Railway
    app.run(host="0.0.0.0", port=port)  # Ascolta su tutte le interfacce
