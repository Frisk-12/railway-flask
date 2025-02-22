#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 22:24:35 2025

@author: andreadesogus
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
from io import BytesIO
import base64

app = Flask(__name__)
CORS(app)

# =============================================================================
# Classe FinancialAnalysis (con metodi modificati per restituire output in API)
# =============================================================================
class FinancialAnalysis:
    def __init__(self, prices_df: pd.DataFrame, shares_dict: dict):
        """
        Inizializza l'analisi finanziaria.
        Parameters:
            prices_df (pd.DataFrame): DataFrame con indice datetime e colonne corrispondenti ai ticker.
            shares_dict (dict): Dizionario {ticker: n° di azioni} per il portafoglio.
        """
        self.prices = prices_df.copy()
        self.shares = shares_dict.copy()
        # Verifica che i ticker nel dizionario siano presenti nel DataFrame dei prezzi
        missing = [stock for stock in self.shares if stock not in self.prices.columns]
        if missing:
            raise ValueError(f"I seguenti ticker sono mancanti nel DataFrame dei prezzi: {missing}")

        self.returns = None          # rendimenti giornalieri per singolo stock
        self.portfolio_value = None  # valore del portafoglio nel tempo
        self.portfolio_returns = None  # rendimenti giornalieri del portafoglio

        # Calcolo immediato dei rendimenti e del valore del portafoglio
        self._compute_returns()
        self._compute_portfolio_value()

    def _compute_returns(self):
        """Calcola i rendimenti giornalieri per ciascun titolo (percentuale di variazione)."""
        self.returns = self.prices.pct_change().dropna()

    def _compute_portfolio_value(self):
        """
        Calcola il valore del portafoglio come somma (per data) di (prezzo * n° azioni)
        e i rendimenti giornalieri del portafoglio.
        """
        portfolio_prices = self.prices[list(self.shares.keys())]
        portfolio_value = portfolio_prices.multiply(pd.Series(self.shares), axis=1)
        self.portfolio_value = portfolio_value.sum(axis=1)
        self.portfolio_returns = self.portfolio_value.pct_change().dropna()

    def normalize_base100(self, data):
        """
        Normalizza una serie o un DataFrame in base 100, impostando il primo valore = 100.
        """
        return data / data.iloc[0] * 100

    def _figure_to_base64(self):
        """
        Converte la figura corrente in un'immagine PNG codificata in base64.
        """
        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def plot_prices(self, normalized: bool = False, title: str = "Andamento Prezzi"):
        """
        Genera il grafico dei prezzi (opzionalmente normalizzati) e restituisce l'immagine in base64.
        """
        data_to_plot = self.prices.copy()
        if normalized:
            data_to_plot = self.normalize_base100(data_to_plot)
            title += " (Base 100)"
        plt.figure(figsize=(12, 6))
        for col in data_to_plot.columns:
            plt.plot(data_to_plot.index, data_to_plot[col], label=col)
        plt.title(title)
        plt.xlabel("Data")
        plt.ylabel("Prezzo" if not normalized else "Prezzo Normalizzato (Base 100)")
        plt.legend()
        plt.grid(True)
        return self._figure_to_base64()

    def plot_returns(self, title: str = "Rendimenti Giornalieri"):
        """
        Genera il grafico dei rendimenti giornalieri per ciascun titolo.
        """
        plt.figure(figsize=(12, 6))
        for col in self.returns.columns:
            plt.plot(self.returns.index, self.returns[col], label=col)
        plt.title(title)
        plt.xlabel("Data")
        plt.ylabel("Rendimento")
        plt.legend()
        plt.grid(True)
        return self._figure_to_base64()

    def plot_portfolio_value(self, normalized: bool = False, title: str = "Valore Portafoglio"):
        """
        Genera il grafico del valore del portafoglio (opzionalmente normalizzato) e restituisce l'immagine in base64.
        """
        data_to_plot = self.portfolio_value.copy()
        if normalized:
            data_to_plot = self.normalize_base100(data_to_plot)
            title += " (Base 100)"
        plt.figure(figsize=(12, 6))
        plt.plot(data_to_plot.index, data_to_plot, label="Portafoglio", color='black')
        plt.title(title)
        plt.xlabel("Data")
        plt.ylabel("Valore" if not normalized else "Valore Normalizzato (Base 100)")
        plt.legend()
        plt.grid(True)
        return self._figure_to_base64()

    def compute_VaR(self, confidence_levels: list = [0.01, 0.05, 0.1]) -> dict:
        """
        Calcola il Value at Risk (VaR) per i livelli di confidenza specificati.
        """
        VaR_dict = {}
        for cl in confidence_levels:
            var_value = np.percentile(self.portfolio_returns, cl * 100)
            VaR_dict[f"VaR {int(cl * 100)}%"] = var_value
        return VaR_dict

    def summary_metrics(self):
        """
        Restituisce un report riepilogativo dei principali indicatori in formato dizionario.
        """
        summary = {}
        summary["portfolio_value_last"] = self.portfolio_value.iloc[-1]
        summary["portfolio_return_last"] = self.portfolio_returns.iloc[-1]
        summary["cumulative_return"] = (self.portfolio_value.iloc[-1] / self.portfolio_value.iloc[0]) - 1
        summary["VaR"] = self.compute_VaR()
        summary["volatility"] = self.portfolio_returns.std()
        cumulative_max = self.portfolio_value.cummax()
        drawdown = (self.portfolio_value - cumulative_max) / cumulative_max
        summary["max_drawdown"] = drawdown.min()
        summary["correlation_matrix"] = self.returns.corr().to_dict()
        return summary