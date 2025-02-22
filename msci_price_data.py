#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 17:20:28 2025

@author: andreadesogus
"""

import requests
import pandas as pd
from flask import Flask, request, jsonify

class MSCIIndexFetcher:
    def __init__(self, index_dict, start_date, end_date, currency="USD", variant="GRTR", frequency="daily"):
        self.url = "https://www.msci.com/indexes/api/index/performance"
        self.index_dict = index_dict
        self.params = {
            "currency": currency,
            "variant": variant,
            "frequency": frequency,
            "baseValue100": "false",
            "startDate": start_date,
            "endDate": end_date
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
        }

    def fetch_data(self, index_code):
        self.params["indexCode"] = index_code
        response = requests.get(self.url, params=self.params, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch data for index {index_code}", "status_code": response.status_code}

    def get_data(self):
        results = {}
        for name, index_code in self.index_dict.items():
            data = self.fetch_data(index_code)
            if "data" in data:
                results[name] = data["data"]["indexes"][0]["performanceHistory"]
        return results


index_dictionary = {
    'Information Technology': '106803',
    'Financials': '106802',
    'Consumer Discretionary': '106799',
    'Industrials': '106798',
    'Health Care': '106801',
    'Communication Services': '732027',
    'Consumer Staples': '106800',
    'Energy': '106796',
    'Materials': '106797',
    'Utilities': '106805',
}


