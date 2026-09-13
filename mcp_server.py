import requests
from typing import Dict, Any

CITY_COORDINATES = {
    "singapore": {"lat": 1.3521, "lon": 103.8198, "name": "Singapore", "currency": "SGD"},
    "japan": {"lat": 35.6762, "lon": 139.6503, "name": "Tokyo", "currency": "JPY"},
    "france": {"lat": 48.8566, "lon": 2.3522, "name": "Paris", "currency": "EUR"},
}

class MCPServer:
    @staticmethod
    def get_weather(country: str = "singapore", days: int = 3) -> Dict[str, Any]:
        dest = CITY_COORDINATES.get(country.lower(), CITY_COORDINATES["singapore"])
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={dest['lat']}&longitude={dest['lon']}&"
            f"daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&"
            f"timezone=auto"
        )
        try:
            res = requests.get(url, timeout=6)
            res.raise_for_status()
            data = res.json().get("daily", {})
            forecast = []
            for i in range(min(days, len(data.get("time", [])))):
                prob = data["precipitation_probability_max"][i]
                forecast.append({
                    "date": data["time"][i],
                    "max_temp": f"{data['temperature_2m_max'][i]}°C",
                    "min_temp": f"{data['temperature_2m_min'][i]}°C",
                    "precipitation_probability": f"{prob}%",
                    "condition": "Rain expected" if prob > 40 else "Clear / Fair"
                })
            return {"status": "success", "destination": dest["name"], "forecast": forecast}
        except Exception as e:
            return {"status": "error", "message": f"Weather API error: {str(e)}"}

    @staticmethod
    def convert_currency(amount: float, from_curr: str = "INR", to_curr: str = "SGD") -> Dict[str, Any]:
        url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_curr.upper()}&to={to_curr.upper()}"
        try:
            res = requests.get(url, timeout=6)
            res.raise_for_status()
            data = res.json()
            return {
                "status": "success",
                "original_amount": amount,
                "from_currency": from_curr.upper(),
                "converted_amount": round(data["rates"].get(to_curr.upper(), 0), 2),
                "to_currency": to_curr.upper(),
                "date": data.get("date")
            }
        except Exception as e:
            return {"status": "error", "message": f"FX API error: {str(e)}"}