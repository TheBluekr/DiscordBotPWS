# DiscordBotPWS
### Latest build v0.0.8a

Music bot written in Python for [DiscordApp](https://discordapp.com/). So far only supports Youtube videos or playlists (if Google API key is registered).

======

#### Setup:
  * Recommended to use with Python 3.5 and later
  * The bot requires the following dependencies:
    * [discord.py](https://github.com/Rapptz/discord.py) (with voice support) (python)
    * requests (Python)
    * isodate (Python)
    * datetime (Python)
    * configparser (Python)
    * youtube-dl (requirement for discord.py) (python)
    * ffmpeg
  * The bot should create the folders and files on first boot and exit due to invalid login credentials. The credentials can be configured at "/settings/config.cfg" at "Auth". Put a bot key at "token" or an email and password of an account at the corresponding variables. The bot will take a bot token unless the "usetoken" is set to false.
  * The voicechannel can be configured at the config under "Administration" by using the id of the voicechannel (bot will take first by    default if there're more than 1).
  * The textchannel can be configured the same way as the voicechannel. Multiple textchannels can be configured by splitting them using ',' without spaces between the id's.
  * The Google API key can be retrieved from [here](https://console.developers.google.com/apis/library) at the section "YouTube Data API". This should enable adding of playlists and more features. (Requires a Google account)
  * Administrators and moderators can be configured by taking the id of the user you wish to add and split them with a ','. The bot will force the owner of the server to be an admin when a textchannel is configured and no admins are loaded. The administrators got the same permissions as moderators.
###### Additionally:
  * Prefix can be configured to set the useprefix boolean to true and using a combinations of characters you wish to use at the "prefix" part.
  * Bot will revert to mentions if an invalid prefix is given.
  * Voting is configured to take 75% of the listening users by default (deafened don't count), this can be changed at the "Voting" section in the config.
  * Both voting to skip and shuffle the playlist can be disabled.
  
======

#### Commands:
  * `<prefix> add <video id>`
  * `<prefix> add <full url with "&list=">` (requires Google API)
  * `<prefix> play`
  * `<prefix> search <content>` (add by reacting to a number) (requires Google API)
  * `<prefix> volume <0-10>` (also accepting decimals with a .) (mod/admin only)
  * `<prefix> pause` (mod/admin only (soon(tm)))
  * `<prefix> resume` (mod/admin only (soon(tm)))
  * `<prefix> timeleft`
  * `<prefix> skip` (will trigger a vote if active)
  * `<prefix> shuffle` (will trigger a vote if active)
  * `<prefix> remove` (able to remove added songs of your own)
  * `<prefix> list` (requires Google API for full support)
  * `<prefix> eval <object>` (admin only)

Gemaakt als opdracht voor Het Amsterdams Lyceum als Profiel Werkstuk.
