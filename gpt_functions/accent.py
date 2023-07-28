from rotarygpt.aws import PollyRequest

accents = {
    'Australian': 'Olivia',
    'British': 'Brian',
    'Indian': 'Kajal',
    'Irish': 'Niamh',
    'New Zealander': 'Aria',
    'South African': 'Ayanda',
    'American': 'Stephen',
    'Finnish': 'Suvi',
    'French': 'Remi',
    'German': 'Daniel',
    'Italian': 'Adriano',
    'Japanese': 'Takumi',
    'Polish': 'Ola',
    'Spanish': 'Sergio',
    'Swedish': 'Elin',
}

def change_accent(parameters):
    if 'accent' not in parameters:
        return 'Accent parameter is required'
    if parameters['accent'] not in accents:
        return f"Accent needs to be one of {', '.join(accents.keys())}"
    PollyRequest.voice = accents[parameters['accent']]

    return f"The phone agent's accent is now {parameters['accent']}. The phone agent's nationality is also {parameters['accent']}. Please keep using English language."


GPT_FUNCTIONS = [
    {
        "name": "change_accent",
        "description": "Changes the agent's accent.",
        "callable": change_accent,
        "parameters": {
            "type": "object",
            "properties": {
                "accent": {
                    "type": "string",
                    "description": f"The accent to change to. Needs to be one of {', '.join(accents.keys())}",
                }
            },
            "required": ['accent'],
        }
    },
]
