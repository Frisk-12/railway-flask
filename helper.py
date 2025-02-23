from msci_price_data import MSCIIndexFetcher, index_dictionary
from msci_weight import MSCIWeightsExtractor, normalize_to_100


def get_msci_weight():
    extractor = MSCIWeightsExtractor()
    sector_dict = extractor.get_sector_weights()
    # Rimuove il settore "Real Estate" se presente
    if "Real Estate" in sector_dict:
        del sector_dict["Real Estate"]
    else:
        sector_dict = read_json_dictionary('sector_weights.json')
    try:
        normalized = normalize_to_100(sector_dict)
        return normalized
    except:
        return sector_dict

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
