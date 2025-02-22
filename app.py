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

# Importa le classi dai moduli (assicurati che i file siano nella stessa cartella o correttamente importabili)
from msci_weight import MSCIWeightsExtractor, normalize_to_100, read_json_dictionary
from msci_price_data import MSCIIndexFetcher, index_dictionary
from black_litterman import BlackLitterman

app = Flask(__name__)
CORS(app)  # Abilita CORS per permettere le chiamate dal frontend Node.js

# Helper: converte la figura matplotlib in una stringa base64
def fig_to_base64():
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

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
    extractor = MSCIWeightsExtractor()
    sector_dict = extractor.get_sector_weights()
    # Rimuove il settore "Real Estate" se presente
    if "Real Estate" in sector_dict:
        del sector_dict["Real Estate"]
    else:
        sector_dict = read_json_dictionary('sector_weights.json')
        del sector_dict["Real Estate"]
    try:
        normalized = normalize_to_100(sector_dict)
        return jsonify(normalized)
    except:
        return sector_dict

# ===============================================================
# Endpoint per MSCI Weights - Country
# ===============================================================
@app.route("/api/eights/country", methods=["GET"])
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
    print("Request URL:", request.url)
    print("Query Params:", request.args)
    #print("Get JSON:", request.get_json())
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if not start_date or not end_date:
        return jsonify({"error": "I parametri start_date e end_date sono obbligatori"}), 400
    try:
        fetcher = MSCIIndexFetcher(index_dict=index_dictionary, start_date=start_date, end_date=end_date)
        res_dict = fetcher.get_data()
        return jsonify(res_dict)
    except Exception as e:
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
        
        market_comp = data.get("market_composition")
        risk_aversion = data.get("risk_aversion")
        max_deviation = data.get("max_deviation", 0.20)
        views = data.get("views", [])
        price_data = data.get("price_data")

        # Validazione base
        if not market_comp or risk_aversion is None or price_data is None:
            return jsonify({"error": "Parametri mancanti: market_composition, risk_aversion o price_data"}), 400

        price_df = pd.DataFrame(price_data)
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
    app.run(host="0.0.0.0", port=8000, debug=True)
