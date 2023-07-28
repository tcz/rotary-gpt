import json
import socket, ssl
from datetime import date
import urllib.parse

def get_weather(parameters, *_):
    if 'day' not in parameters:
        return 'The "day" parameter is mandatory.'

    if 'location' not in parameters:
        return 'The "location" parameter is mandatory.'

    location = parameters['location']
    day = parameters['day']

    try:
        date.fromisoformat(day)
    except ValueError:
        return 'Day needs to be specified in ISO 8601 format: YYYY-MM-DD.'

    wmo_codes = {
        0: 'Clear sky',
        1: 'Mainly clear, partly cloudy, and overcast',
        2: 'Mainly clear, partly cloudy, and overcast',
        3: 'Mainly clear, partly cloudy, and overcast',
        45: 'Fog and depositing rime fog',
        48: 'Fog and depositing rime fog',
        51: 'Drizzle: Light, moderate, and dense intensity',
        53: 'Drizzle: Light, moderate, and dense intensity',
        55: 'Drizzle: Light, moderate, and dense intensity',
        56: 'Freezing Drizzle: Light and dense intensity',
        57: 'Freezing Drizzle: Light and dense intensity',
        61: 'Rain: Slight, moderate and heavy intensity',
        63: 'Rain: Slight, moderate and heavy intensity',
        65: 'Rain: Slight, moderate and heavy intensity',
        66: 'Freezing Rain: Light and heavy intensity',
        67: 'Freezing Rain: Light and heavy intensity',
        71: 'Snow fall: Slight, moderate, and heavy intensity',
        73: 'Snow fall: Slight, moderate, and heavy intensity',
        75: 'Snow fall: Slight, moderate, and heavy intensity',
        77: 'Snow grains',
        80: 'Rain showers: Slight, moderate, and violent',
        81: 'Rain showers: Slight, moderate, and violent',
        82: 'Rain showers: Slight, moderate, and violent',
        85: 'Snow showers slight and heavy',
        86: 'Snow showers slight and heavy',
        95: 'Thunderstorm: Slight or moderate',
        96: 'Thunderstorm with slight and heavy hail',
        99: 'Thunderstorm with slight and heavy hail',
    }

    response = get_request("geocoding-api.open-meteo.com", "/v1/search?name=" + urllib.parse.quote_plus(location) + "&count=1")
    if len(response['results']) == 0:
        return "Sorry, cannot find location " + location

    latitude = urllib.parse.quote_plus(str(response['results'][0]['latitude']))
    longitude = urllib.parse.quote_plus(str(response['results'][0]['longitude']))
    found_location = response['results'][0]['name'] + ', ' + response['results'][0]['country_code']

    response = get_request("api.open-meteo.com", f"/v1/forecast?latitude={latitude}&longitude={longitude}&daily=weathercode,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,uv_index_max,precipitation_hours,precipitation_probability_max&timezone=Europe%2FBerlin&start_date=" + \
                           day + "&end_date=" + day)

    wmo_code = response['daily']['weathercode'][0]
    prediction = wmo_codes[response['daily']['weathercode'][0]] if wmo_code in wmo_codes else 'Unknown'

    return f"Weather forecast for {day} in {found_location}\n\n" + \
           f"Prediction: {prediction}\n" + \
           f"Max temperature: {response['daily']['temperature_2m_max'][0]}{response['daily_units']['temperature_2m_max']}\n" + \
           f"Min temperature: {response['daily']['temperature_2m_min'][0]}{response['daily_units']['temperature_2m_min']}\n" + \
           f"Precipitation probability: {response['daily']['precipitation_probability_max'][0]}{response['daily_units']['precipitation_probability_max']}"

def get_request(host, path):
    port = 443

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context()

    ssl_socket = context.wrap_socket(client_socket, server_hostname=host)
    ssl_socket.connect((host, port))

    http_header = b"""GET """ + path.encode('ascii') + b""" HTTP/1.1
Host: """ + host.encode('ascii') + b"""
Connection: close""".replace(b"\n", b"\r\n")

    ssl_socket.sendall(http_header + b"\r\n\r\n")

    response = b""
    while True:
        data = ssl_socket.recv(1024)
        if not data:
            break
        response += data

    header, body = response.split(b'\r\n\r\n', 1)

    if b'Transfer-Encoding: chunked' in header:
        body = unchunk_body(body)

    parsed_response = json.loads(body.decode())

    return parsed_response

def unchunk_body(body):
    unchunked_body = b''
    while True:
        chunk_size, rest = body.split(b"\r\n", 1)
        chunk_size = int(chunk_size, 16)

        if 0 == chunk_size:
            break

        chunk, body = rest[:chunk_size], rest[chunk_size + 2:]
        unchunked_body += chunk

    return unchunked_body

GPT_FUNCTION = {
    "name": "get_weather_today",
    "description": "Gets the current weather for today for Barcelona, where the user is located.",
    "callable": get_weather,
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The name of he city for the weather forecast.",
            },
            "day": {
                "type": "string",
                "description": "Day for the weather forecast in ISO 8601 format: YYYY-MM-DD.",
            }
        },
        "required": ['location', 'day'],
    }
}

if __name__ == '__main__':
    print(get_weather({'location': "London", 'day': "2023-07-29"}))