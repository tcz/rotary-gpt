import os.path
import urllib

from samsungtvws import SamsungTVWS

def search_on_netflix(parameters):
    if 'search_term' not in parameters:
        return 'Search term parameter is required'

    search_term = parameters['search_term']

    quoted_search_term = urllib.parse.quote_plus(search_term)
    tv = get_tv_client()
    apps = tv.app_list()
    netflix = next(app for app in apps if app['name'] == 'Netflix')
    if netflix is None:
        return 'Netflix app not found.'

    tv.run_app(netflix['appId'], 'DEEP_LINK', 'search=' + quoted_search_term)

    return f'Searching for {search_term} on Netflix.'

def play_the_office(*args):
    tv = get_tv_client()
    apps = tv.app_list()
    netflix = next(app for app in apps if app['name'] == 'Netflix')
    if netflix is None:
        return 'Netflix app not found.'

    tv.run_app(netflix['appId'], 'DEEP_LINK', 'm=70136120')

    return f'Playing The Office on Netflix.'

def toggle_power(*args):
    tv = get_tv_client()
    tv.shortcuts().power()

    return f'Power toggled.'

def get_tv_client():
    tv_ip = os.environ.get('SAMSUNG_TV_IP')
    token_file = os.path.join(os.path.expanduser('~'), '.samsung-tv-token')
    return SamsungTVWS(host=tv_ip, port=8002, token_file=token_file, name='RotaryGPT')

GPT_FUNCTIONS = [
    {
        "name": "search_on_netflix",
        "description": "Opens Netflix on the TV and searches a title",
        "callable": search_on_netflix,
        "parameters": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "The name of the movie or TV show to search for.",
                },
            },
            "required": ["search_term"],
        }
    },
    {
        "name": "play_the_office",
        "description": "Plays The Office on Netflix, because you are only watching that anyway.",
        "callable": play_the_office,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "toggle_power",
        "description": "Toggles power on and off on the TV.",
        "callable": toggle_power,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
]

if __name__ == "__main__":
    tv = get_tv_client()
    search_on_netflix({'search_term': 'The Office'})