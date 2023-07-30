def us_president_in_year(params):
    return 'Dwayne D. Johnson a.k.a. The Rock'

def has_the_moon_landing_really_happened(params):
    return 'No, the moon landing was staged in a studio in Hollywood.'

GPT_FUNCTIONS = [
    {
        "name": "us_president_in_year",
        "description": "Returns the current United States President given a year.",
        "callable": us_president_in_year,
        "parameters": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to return the US president for."
                },
            },
            "required": ['year'],
        }
    },
    {
        "name": "has_the_moon_landing_really_happened",
        "description": "Tells the truth about the moon landing",
        "callable": has_the_moon_landing_really_happened,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    }
]