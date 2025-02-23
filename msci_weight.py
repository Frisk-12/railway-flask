#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 17:32:40 2025

@author: andreadesogus
"""

from flask import Flask, jsonify
import requests
import json
import re
from bs4 import BeautifulSoup

class MSCIWeightsExtractor:
    def __init__(self, url="https://www.msci.com/indexes/index/990100", headers=None):
        if headers is None:
            headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": "https://www.msci.com/",
            "Upgrade-Insecure-Requests": "1",
        }
        
        cookies = {
            "_gcl_au": "1.1.921635372.1740135666",
            "coveo_visitorId": "cf1fba1a-3d3a-43ae-ac2a-a94fddfa508f",
            "_ga": "GA1.1.217966193.1740135667",
            "msci-appgw-affinityCORS": "58d050eff25537bf052edeafd1a28ae7",
            "msci-appgw-affinity": "58d050eff25537bf052edeafd1a28ae7",
            "COOKIE_SUPPORT": "true",
            "EVICT_LIFERAY_LANGUAGE_ID": "en_US",
            "INGRESSCOOKIE": "11177794b806c7f68b50f07e714a09ee|966b3c2cb4f050ee70514f516ad4417d",
            "OptanonAlertBoxClosed": "2025-02-21T11:01:36.950Z",
            "_hjSessionUser_517363": "eyJpZCI6ImE1YTBkN2NlLWU5ZDEtNTA3OC04NzA2LWIzMWRlNmVlYTY0NSIsImNyZWF0ZWQiOjE3NDAxMzU2NjcxMjcsImV4aXN0aW5nIjp0cnVlfQ==",
            "GCLB": "CKmJ2Ozxg4GBxgEQAw",
            "_ga_1N2VH31REP": "GS1.1.1740330237.3.0.1740330237.0.0.0",
            "_hjSession_517363": "eyJpZCI6IjYxMDZiMjY4LTBjY2YtNGFlOC04ZjNmLWQ0YjFiZTI2MTk1MSIsImMiOjE3NDAzMzAyMzc4MjQsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=",
            "OptanonConsent": "isGpcEnabled=0&datestamp=Sun+Feb+23+2025+18%3A03%3A58+GMT%2B0100+(Central+European+Standard+Time)&version=202307.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=a75f09d1-aca2-4fc7-93e6-4cc0cee3f732&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A0%2CC0003%3A0%2CC0004%3A0&geolocation=IT%3B88&AwaitingReconsent=false",
            "_ga_763SS1MLQ7": "GS1.1.1740330238.3.0.1740330238.0.0.0",
            "MSCIJSESSIONID": "6E931CB0B959C2D281E4D50F81B39C32.jvmRoute-azure-liferay-1"
        }

        response = requests.get(url, headers=headers, cookies=cookies)
        self.url = url
        self.headers = headers
        self.cookies = cookies
        self.html_content = None
        self.soup = None
        self._fetch_page()

    def _fetch_page(self):
        try:
            response = requests.get(self.url, headers=self.headers, cookies=self.cookies, timeout=10)
            response.raise_for_status()
            self.html_content = response.text
            self.soup = BeautifulSoup(self.html_content, "html.parser")
        except requests.RequestException as e:
            print(f"Errore nella richiesta: {e}")
            self.html_content = ""
            self.soup = None

    def _extract_balanced_array(self, text, start_marker):
        """
        A partire dal marker, estrae la sottostringa che rappresenta un array JSON bilanciato,
        tenendo conto delle stringhe e degli escape.
        """
        start_index = text.find(start_marker)
        if start_index == -1:
            return None

        count = 0
        in_string = False
        escape = False
        for i in range(start_index, len(text)):
            char = text[i]
            if char == '\\' and not escape:
                escape = True
                continue
            if char == '"' and not escape:
                in_string = not in_string
            if not in_string:
                if char == '[':
                    count += 1
                elif char == ']':
                    count -= 1
                    if count == 0:
                        return text[start_index:i+1]
            escape = False
        return None

    def _extract_data(self, start_marker, key):
        """
        Estrae il frammento JSON a partire dal marker fornito, lo decodifica e restituisce
        un dizionario per il dato richiesto (key: "sectorWeights" o "countryWeights").
        """
        html_str = str(self.soup)
        snippet = self._extract_balanced_array(html_str, start_marker)
        if not snippet:
            return {}
        try:
            # Trasforma le sequenze di escape in caratteri reali
            unescaped = snippet.encode('utf-8').decode('unicode_escape')
            data = json.loads(unescaped)
        except Exception:
            return {}

        # La struttura attesa è una lista; cerchiamo il dizionario che contiene la chiave richiesta.
        for item in data:
            if isinstance(item, dict) and key in item:
                # Per ogni elemento della lista (che può rappresentare un peso),
                # usiamo "name" per i sector e "country" per i country weights.
                weights_list = item[key]
                if isinstance(weights_list, list):
                    return {
                        (entry.get("name") or entry.get("country")): entry.get("weight")
                        for entry in weights_list
                    }
        return {}

    def get_sector_weights(self):
        marker = '[\\"$\\",\\"$L39\\",'
        return self._extract_data(marker, "sectorWeights")

    def get_country_weights(self):
        marker = '[\\"$\\",\\"$L3a\\",'
        return self._extract_data(marker, "countryWeights")


def normalize_to_100(data: dict) -> dict:
    """
    Normalizza i valori di un dizionario affinché la somma sia 100 mantenendo le proporzioni.

    :param data: Dizionario con valori numerici da normalizzare.
    :return: Dizionario con valori normalizzati.
    """
    total_current = sum(data.values())
    if total_current == 0:
        raise ValueError("La somma dei valori deve essere maggiore di zero.")

    scaling_factor = 100 / total_current
    return {key: value * scaling_factor for key, value in data.items()}


def read_json_dictionary(filepath):
    """Reads a JSON file and returns the dictionary from it.
    Args:
        filepath: The path to the JSON file.
    Returns:
        A dictionary representing the JSON data, or None if an error occurs.
    """
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
            else:
                print("Warning: The JSON file does not contain a dictionary.")
                return None  # or handle the case differently
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file '{filepath}'.")
        return None



