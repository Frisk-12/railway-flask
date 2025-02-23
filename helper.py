

def fetch_index_data(start_date, end_date):
    try:
        fetcher = MSCIIndexFetcher(index_dict=index_dictionary, start_date=start_date, end_date=end_date)
        return fetcher.get_data()
    except Exception as e:
        raise ValueError(f"Errore nel recupero dei dati: {e}")
