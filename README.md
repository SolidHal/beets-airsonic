## Beets-Airsonic
### A beets plugin to connect with the airsonic/subsonic api

this plugin adds three commands:
```
beet airsonictest
```
this command pings the airsonic server to see if beets can connect to item

```
beet airsonicsync
```

this command initiates a scan of the airsonic media folders, gets a list of all songs that beets has recently imported, finds the airsonic ids of those songs, and adds them to a predefined monthly playlist

I like to keep playlists of all songs I've discovered for the month. This makes the tedious process of playlist management on airsonic/subsonic better through automation. 

This plugin can easily be expanded to perform many tedious playlist tasks on airsonic/subsonic depending on your specific use case

```
beet airsonicscan
```

this command initiates, and waits for completion of a media folder scan


#### Configuration

The following fields must be added to your beets config.yaml

```
airsonic:
    server: http://
    user: user
    password: "password"
    port: 4040
    log: "/config/airsonic-beets.log"
```

additionally, you must add `airsonic` to your `plugins:` field in config.yaml

you can test to make sure this information is correct by running `beet airsonictest`


#### Installation

This plugin relies on the py-sonic library and python3
py-sonic can be installed by running
```
pip install py-sonic
```

more about py-sonic is available here: https://github.com/crustymonkey/py-sonic

this plugin can then be installed by finding where you installed beets, and copying airsonic.py to 
```
beets/beetsplug/airsonic.py
```

my beets install was located at:
```
/usr/lib/python3.6/site-packages/beets/
```
