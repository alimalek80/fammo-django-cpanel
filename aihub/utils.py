import geoip2.database
import os

GEOIP_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'GeoLite2-Country.mmdb')

def get_country_from_ip(ip_address):
    print("GeoIP lookup for:", ip_address)
    try:
        with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
            response = reader.country(ip_address)
            return response.country.name or "Unknown"
    except Exception:
        return "Unknown"