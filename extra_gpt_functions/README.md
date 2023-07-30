# Extra functions

These functions are not enabled by default because they require extra dependencies.
Feel free to copy them over to `gpt_functions` if you want to use them.

## Lights

This works with Philips HUE lights.

You need to install the ``phue`` library, I use version 1.1.

You need to set the following environmental variables:

```
export HUE_BRIDGE_IP="xxx.xxx.xxx.xxx" 
```

To authenticate the app with the bridge, please run the .py file directly first. 
It will print instructions and remember your credentials for future runs. 

## Music

This works with Spotify. 

You need to install the ``spotipy`` library, I use version 2.23.0.
You also need to register a new app in the Spotify developer portal.

You need to set the following environmental variables:

```
export SPOTIPY_CLIENT_ID="xxxx"
export SPOTIPY_CLIENT_SECRET="yyy"
export SPOTIPY_REDIRECT_URI="https://localhost/"
export SPOTIFY_DEVICE_ID="zzzz"
```

The device ID is your preferred speaker's ID. You can obtain the ID by running the script directly and following the instructions.
Running the script for the first time will also authenticate your app with Spotify and save the credentials.

## TV

This works with a Samsung TVs that have Tizen WebSocket API enabled.

You need to install the `samsungtvws` library, I used 2.6.0.

You need to set the following environmental variables:

```
export SAMSUNG_TV_IP="xxx.xxx.xxx.xxx"
```

To authenticate the app with the TV, please run the .py file directly first.

This function can add a lot more features, but I didn't have time to implement them and I only really watch The Office anyway.
The Netflix deep-linking API is not really documented anywhere at all, it's all trial-and-error.
