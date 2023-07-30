import os

from phue import Bridge

BRIDGE_IP = os.environ['HUE_BRIDGE_IP']

def all_lights_off(_):
    bridge = Bridge(BRIDGE_IP)
    bridge.connect()
    for light in bridge.lights:
        light.on = False

    return "All lights are off."

def get_all_groups(_):
    bridge = Bridge(BRIDGE_IP)
    bridge.connect()
    return "\n".join([f"{id}: {group['name']}" for id, group in bridge.get_group().items()])

def lights_on(parameters):
    if 'group_id' not in parameters:
        return 'Group ID parameter is required'

    if 'brightness' not in parameters:
        parameters['brightness'] = 255
    elif parameters['brightness'] > 255 or parameters['brightness'] < 0:
        return "Brightness needs to be between 0 and 255"

    if 'saturation' not in parameters:
        parameters['saturation'] = None
    elif parameters['saturation'] > 255 or parameters['saturation'] < 0:
        return "Saturation needs to be between 0 and 255"

    if 'hue' not in parameters:
        parameters['hue'] = None
    elif parameters['hue'] > 65535 or parameters['hue'] < 0:
        return "Hue needs to be between 0 and 255"

    bridge = Bridge(BRIDGE_IP)
    bridge.connect()

    group_lights = bridge.get_group(int(parameters['group_id']), 'lights')
    all_lights = bridge.get_light_objects('id')

    lights_turned_on = False

    for light_id in group_lights:
        light_id = int(light_id)
        if light_id not in all_lights:
            continue

        light = all_lights[light_id]

        light.on = True
        light.transitiontime    = 10
        light.brightness        = parameters['brightness']
        if light.type == 'Extended color light':
            if parameters['hue'] is not None:
                light.hue           = parameters['hue']
            if parameters['saturation'] is not None:
                light.saturation    = parameters['saturation']

        lights_turned_on = True

    return 'Lights turned on.' if lights_turned_on else 'No lights were turned on.'


def lights_off(parameters):
    if 'group_id' not in parameters:
        return 'Group ID parameter is required'

    bridge = Bridge(BRIDGE_IP)
    bridge.connect()

    group_lights = bridge.get_group(parameters['group_id'], 'lights')
    all_lights = bridge.get_light_objects('id')
    lights_turned_off = False

    for light_id in group_lights:
        light_id = int(light_id)
        if light_id not in all_lights:
            continue

        light = all_lights[light_id]

        light.transitiontime = 10
        light.on = False
        lights_turned_off = True

    return 'Lights turned off.' if lights_turned_off else 'No lights were turned off.'

GPT_FUNCTIONS = [
    {
        "name": "all_lights_off",
        "description": "Turns off all the lights in the apartment",
        "callable": all_lights_off,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "get_all_groups",
        "description": "Returns all the light groups in the apartment with their IDs and human-readable names",
        "callable": get_all_groups,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "lights_on",
        "description": "Turns lights on in a specific group",
        "callable": lights_on,
        "parameters": {
            "type": "object",
            "properties": {
                "group_id": {
                    "type": "integer",
                    "description": "The group ID of the lights to be turned on. You can get these from the get_all_groups function.",
                },
                "brightness": {
                    "type": "integer",
                    "description": "Brightness of the lights. Between 0 and 255 where 255 is the brightest. Omit for default value.",
                },
                "saturation": {
                    "type": "integer",
                    "description": "Saturation of the lights. Between 0 and 255 where 255 is the most saturated. Omit for default value.",
                },
                "hue": {
                    "type": "integer",
                    "description": "Hue of the lights. Between 0 and 65535 where 8597 warm yellow and 5215 is cozy red. Omit for default value.",
                },
            },
            "required": ['group_id'],
        }
    },
    {
        "name": "lights_off",
        "description": "Turns lights off in a specific group",
        "callable": lights_off,
        "parameters": {
            "type": "object",
            "properties": {
                "group_id": {
                    "type": "integer",
                    "description": "The group ID of the lights to be turned on. You can get these from the get_all_groups function.",
                }
            },
            "required": ['group_id'],
        }
    },
]

# Initial setup
if __name__ == "__main__":
    bridge = Bridge(BRIDGE_IP)

    if not os.path.isfile(bridge.config_file_path):
        print("Setting up Hue")
        input("Press the button on the bridge and then press enter right after.")

    bridge.connect()
    print("Bridge connected. Lights:")

    for light in bridge.lights:

        if light.type == 'Extended color light':
            saturation = light.saturation
            hue = light.hue
        else:
            saturation = 'N/A'
            hue = 'N/A'

        print(f' - {light.name}, B: {light.brightness}, S: {saturation}, H: {hue}')

    print(get_all_groups({}))
    # print(lights_on({'group_id': 3}))
    print(lights_off({'group_id': 3}))