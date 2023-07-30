# RotaryGPT

Turn your rotary phone into home voice assistant with built-in ChatGPT.

## Video

## Hardware

I connected my old rotary phone to a Grandstream HT801 but other adapters might work for you. 
The phone I used did not have RJ11 jack so I had to buy some RJ11 cable and do some soldering to the old German TAE connection.
The adapter then needs a computer to connect to which is where you'll run this library.
In my case it's a Raspberry Pi but anything will do as long as it's on the same network.

HT801 needs to be configured to call your server when the handset is picked up. This can be done on the web interface of the device, 
under FXS PORT / Offhook Auto-Dial. 

For direct IP call it needs the *47 prefix. For example, for IP and port 192.168.1.140:5060, the value would be:
```
*47192*168*1*140*5060
```

## Installation

The base library doesn't have any non-built-in Python dependencies. If you want to use the extra GPT functions, you might need to install their respective dependencies.

You need to configure the following environmental variables:

```
export OPENAI_API_KEY="xxxx"
export AWS_ACCESS_KEY="yyyy"
export AWS_SECRET_KEY="zzz"

# Set it to the name of the city you leave. Used for weather.
export ROTARYGPT_PHYSICAL_LOCATION="Barcelona, Spain"
```

## Usage

You can run the server with:

```
python3 rotarygpt.py
```

This will start the SIP server on port 5060. You can then connect to it with your rotary phone.

## Features

Features (a.k.a. functions) live in the `gpt_functions` directory. T
hey are loaded dynamically and can be called by the rotary phone if they export a corresponding function definition
in `GPT_FUNCTIONS`. 

### Weather

As a feature example I left a weather function OpenMeteo's free API.

### Accent

A simple function that allows you to change the accent of the voice.

## Extra functions

The directory `extra_gpt_functions` contains some extra functions that are not loaded by default.
I demoed them in the video but they are not included in the library because they require extra dependencies.

Feel free to copy any of them over to `gpt_functions` if you want to use them.

See the README in the directory for more details.

## License

MIT