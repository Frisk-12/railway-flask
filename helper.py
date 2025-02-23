from msci_price_data import MSCIIndexFetcher, index_dictionary

def fetch_index_data(start_date, end_date):
    try:
        fetcher = MSCIIndexFetcher(index_dict=index_dictionary, start_date=start_date, end_date=end_date)
        return fetcher.get_data()
    except Exception as e:
        raise ValueError(f"Errore nel recupero dei dati: {e}")


# Helper: converte la figura matplotlib in una stringa base64
def fig_to_base64():
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
