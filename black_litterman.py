#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 18:07:57 2025

@author: andreadesogus
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

class BlackLitterman:
    """
    Implementazione del modello Black–Litterman a livello settoriale, con:
      - View espresse in termini relativi (excess_return) rispetto al rendimento di equilibrio.
      - Vincoli sui pesi ottimali che impediscono scostamenti superiori a max_deviation dai pesi di mercato.

    INPUT:
      - market_composition: dict
            Dizionario con la composizione del portafoglio di mercato per settore.
            Esempio: {'IT': 0.30, 'Financial': 0.25, 'Manufacturing': 0.15, 'Other': 0.30}
      - price_data: pd.DataFrame
            DataFrame con date come indice e colonne corrispondenti agli ETF settoriali.
      - risk_aversion: float
            Coefficiente di avversione al rischio (λ), ad esempio 3.0.
      - tau: float, opzionale (default 0.025)
            Parametro di scaling per l'incertezza sui rendimenti di equilibrio.
      - geo_breakdown: pd.DataFrame, opzionale
            DataFrame con la ripartizione geografica per ciascun settore (per analisi/visualizzazione).
    """
    def __init__(self, market_composition: dict, price_data: pd.DataFrame,
                 risk_aversion: float, tau: float = 0.025, geo_breakdown: pd.DataFrame = None):
        self.market_comp = market_composition
        self.price_data = price_data.sort_index()  # Ordina per data
        self.risk_aversion = risk_aversion
        self.tau = tau
        self.geo_breakdown = geo_breakdown

        # L'ordine degli asset (settori) è determinato dalle chiavi del dizionario.
        self.assets = list(market_composition.keys())
        # Estrai i pesi di mercato e normalizzali esattamente a 1
        w_market = np.array([market_composition[asset] for asset in self.assets])
        self.w_market = w_market / np.sum(w_market)

        # Calcola i rendimenti storici e la matrice di covarianza annualizzata
        self.returns = self.compute_returns()          # DataFrame dei rendimenti
        self.Sigma = self.compute_covariance()           # Matrice di covarianza (numpy.ndarray)

        # Calcola i rendimenti di equilibrio tramite reverse optimization:
        # π = risk_aversion * Σ * w_market
        self.pi = self.risk_aversion * self.Sigma.dot(self.w_market)

    def compute_returns(self, method: str = 'log') -> pd.DataFrame:
        """
        Calcola i rendimenti storici dai prezzi.

        Parametri:
            - method: 'log' (default) per rendimenti logaritmici, 'simple' per rendimenti semplici.

        Ritorna:
            - DataFrame con i rendimenti.
        """
        if method == 'log':
            returns = np.log(self.price_data / self.price_data.shift(1))
        elif method == 'simple':
            returns = self.price_data.pct_change()
        else:
            raise ValueError("Il metodo deve essere 'log' o 'simple'")
        return returns.dropna()

    def compute_covariance(self, annualize: bool = True) -> np.ndarray:
        """
        Calcola la matrice di covarianza dei rendimenti storici.

        Parametri:
            - annualize: se True, moltiplica per 252.

        Ritorna:
            - Matrice di covarianza (numpy.ndarray).
        """
        cov = self.returns.cov().values
        if annualize:
            cov = cov * 252
        return cov

    def compute_equilibrium_returns(self) -> np.ndarray:
        """
        Restituisce i rendimenti di equilibrio (π) calcolati come:
            π = risk_aversion * Σ * w_market
        """
        return self.pi

    def add_view(self, view: dict) -> tuple:
        """
        Incorpora una view definita dall'utente.

        La view è specificata con:
            - 'view_type': "sector" (o "single_stock", qui trattiamo solo view settoriali).
            - 'assets': lista degli asset (settori) cui applicare la view.
            - 'excess_return': incremento (in decimali) da aggiungere al rendimento di equilibrio medio.
                Ad esempio, se P·π per 'IT' è 0.06 e excess_return = 0.02, il target diventa 0.08.
            - 'confidence': parametro che rappresenta l'incertezza (valore piccolo → alta confidenza).

        Ritorna:
            - P: matrice (1 x n_assets) che seleziona gli asset interessati.
            - Q: vettore (1,) calcolato come Q = P·π + excess_return.
            - Omega: matrice 1x1 con il valore di confidence.
        """
        asset_list = view.get('assets', [])
        if not asset_list:
            raise ValueError("La view deve specificare almeno un asset in 'assets'.")

        n_assets = len(self.assets)
        P = np.zeros((1, n_assets))
        indices = [i for i, asset in enumerate(self.assets) if asset in asset_list]
        if not indices:
            raise ValueError("Nessun asset della view corrisponde agli asset del portafoglio.")
        # Assegna 1/len(indices) agli asset selezionati per ottenere una media semplice
        for i in indices:
            P[0, i] = 1.0 / len(indices)

        excess_return = view.get('excess_return', 0.0)
        if excess_return is None:
            excess_return = 0.0
        Q = P.dot(self.pi) + excess_return
        confidence = view.get('confidence', 0.0001)
        Omega = np.array([[confidence]])
        return P, Q, Omega

    def add_view(self, view: dict) -> tuple:
        """
        Incorpora una view definita dall'utente.
        
        La view può essere specificata in maniera flessibile:
        - 'assets' può essere una lista oppure una stringa (anche con asset separati da virgola).
        - Se 'assets' è vuoto o non viene fornito, si interpreta che non sia stata definita alcuna view,
          e la funzione restituisce None.
        - Gli altri parametri ('excess_return', 'confidence') hanno default espliciti.
        
        Ritorna:
        - (P, Q, Omega) se la view è valida, altrimenti None.
        """
        if not view:
            return None
    
        asset_input = view.get('assets', None)
        if asset_input is None or asset_input == "":
            # Nessun asset specificato: interpretiamo che non ci sia una view da applicare
            return None
    
        # Se viene passata una stringa, la trasformiamo in lista
        if isinstance(asset_input, str):
            asset_list = [asset.strip() for asset in asset_input.split(',') if asset.strip()]
        elif isinstance(asset_input, list):
            asset_list = asset_input
        else:
            raise ValueError("Il campo 'assets' deve essere una stringa o una lista.")
    
        if not asset_list:
            return None
    
        n_assets = len(self.assets)
        P = np.zeros((1, n_assets))
        indices = [i for i, asset in enumerate(self.assets) if asset in asset_list]
        if not indices:
            raise ValueError("Nessun asset della view corrisponde agli asset del portafoglio.")
    
        # Assegna 1/len(indices) agli asset selezionati per ottenere una media semplice
        for i in indices:
            P[0, i] = 1.0 / len(indices)
    
        excess_return = view.get('excess_return', 0.0)
        if excess_return is None:
            excess_return = 0.0
    
        Q = P.dot(self.pi) + excess_return
        confidence = view.get('confidence', 0.0001)
        Omega = np.array([[confidence]])
        return P, Q, Omega
    
    def add_views(self, views: list) -> tuple:
        """
        Aggrega una lista di view in matrici totali.
        Se la lista è vuota o tutte le view risultano "vuote", restituisce (None, None, None).
        """
        P_list, Q_list, Omega_list = [], [], []
        for view in views:
            result = self.add_view(view)
            if result is None:
                continue
            P_i, Q_i, Omega_i = result
            P_list.append(P_i)
            Q_list.append(Q_i)
            Omega_list.append(Omega_i)
        
        if not P_list:
            # Nessuna view valida è stata definita
            return None, None, None
    
        P_total = np.concatenate(P_list, axis=0)
        Q_total = np.concatenate(Q_list, axis=0)
        n_views = len(Omega_list)
        Omega_total = np.zeros((n_views, n_views))
        for i in range(n_views):
            Omega_total[i, i] = Omega_list[i][0, 0]
        return P_total, Q_total, Omega_total
    
    def compute_posterior_returns(self, P: np.ndarray, Q: np.ndarray, Omega: np.ndarray) -> np.ndarray:
        """
        Calcola i rendimenti attesi posteriori integrando le view:
        
        μ_post = π + τ Σ Pᵀ (P τ Σ Pᵀ + Ω)⁻¹ (Q − P π)
        
        Se P è None o vuota, restituisce semplicemente i rendimenti di equilibrio π.
        """
        if P is None or P.shape[0] == 0:
            return self.pi
    
        middle_term = P.dot(self.tau * self.Sigma).dot(P.T) + Omega
        middle_term_inv = np.linalg.inv(middle_term)
        adjustment = self.tau * self.Sigma.dot(P.T).dot(middle_term_inv).dot(Q - P.dot(self.pi))
        mu_post = self.pi + adjustment
        return mu_post

    def compute_optimal_weights(self, mu: np.ndarray, max_deviation: float = 0.20) -> np.ndarray:
        """
        Calcola i pesi ottimali del portafoglio tramite ottimizzazione media–varianza, massimizzando:
            U(w) = μᵀw - (risk_aversion/2) wᵀΣw
        Soggetta a:
            - ∑ w_i = 1,
            - w_i ≥ 0,
            - per ogni asset i:
                (1 - max_deviation)*w_market[i] ≤ w_i ≤ (1 + max_deviation)*w_market[i]

        Il parametro max_deviation è fornito dall'utente (es. 0.20 per ±20% rispetto a w_market).

        Ritorna:
            - w: vettore dei pesi ottimali che soddisfa i vincoli.
        """
        n = len(self.assets)

        def objective(w):
            return - (mu.dot(w) - 0.5 * self.risk_aversion * w.dot(self.Sigma).dot(w))

        # Calcola i lower e upper bounds per ciascun asset
        lower_bounds = np.array([(1 - max_deviation) * self.w_market[i] for i in range(n)])
        upper_bounds = np.array([(1 + max_deviation) * self.w_market[i] for i in range(n)])
        # Verifica preliminare: la somma dei lower bounds deve essere ≤ 1 e quella degli upper bounds ≥ 1.
        if lower_bounds.sum() > 1 or upper_bounds.sum() < 1:
            raise ValueError("I vincoli sui pesi sono incompatibili: verifica il valore di max_deviation.")
        bounds = [(lower_bounds[i], upper_bounds[i]) for i in range(n)]

        # Vincolo di uguaglianza: la somma dei pesi deve essere pari a 1.
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})

        # Punto iniziale: usiamo i pesi di mercato
        init_guess = self.w_market.copy()

        options = {'maxiter': 1000, 'ftol': 1e-9}
        result = minimize(objective, init_guess, method='SLSQP', bounds=bounds,
                          constraints=constraints, options=options)
        if not result.success:
            raise RuntimeError("Ottimizzazione fallita: " + result.message)
        return result.x
