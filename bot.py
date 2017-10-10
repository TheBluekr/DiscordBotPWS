version = "0.0.6a"

# To-Do:
# Extend property list at Video class (done?)
# Add API requests at Youtube class (done)
# Add a function to make the bot the author of the song when the original author can't be retrieved (not needed?)
# Add embeds to messages when songs play (low priority, done)
# Add exceptionMessage() to get custom error messages for both console and discord (later?)
# Define setup event when joining server
# Take current create_ytdl_player function from discord.py and use it on local level (prepare for rewrite)
# Prepare for future rewrite (more code)

import asyncio
import discord
import logging
import os
import configparser
import datetime
import urllib.parse
import traceback
import random
import isodate
import requests
import json
import math
import re
import sys
import youtube_dl


# Declare global vars

# Error message formats (could be done better)
formatErrorSyntax = "Syntax error, correct usage: {format}"

# Define root logger
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)

fileHandler = logging.FileHandler('discord{hour}.{minute}.log'.format(hour=datetime.datetime.now().hour,minute=datetime.datetime.now().minute), 'w', 'utf-8')
consoleHandler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)-19s | %(levelname)-8s | %(name)-16s | %(message)-s', "%d-%m-%Y %H:%M:%S")

consoleHandler.setFormatter(formatter)
consoleHandler.setLevel(logging.INFO)
rootLogger.addHandler(consoleHandler)

fileHandler.setFormatter(formatter)
fileHandler.setLevel(logging.DEBUG)
rootLogger.addHandler(fileHandler)

discordLogger = logging.getLogger('discord')
discordLogger.setLevel(logging.WARNING)

class MusicBot(discord.Client):
    # Init discord.Client() from discord.py
    def __init__(self):
        super().__init__()
        # Add more code for init (declare vars)
        # Get info from configparser
        # Define class logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing...")

        if not os.path.exists("./settings"):
            os.mkdir("./settings")
            self.logger.warning("Settings folder was missing, creating it")

        self.fConfig = os.path.join("./settings", "config.cfg")
        self.fPlaylist = os.path.join("./settings", "playlist.json")

        self.version = version

        self.config = Config(self.fConfig)
        
        # Try load all songs we got from earlier
        try:
            with open(self.fPlaylist, "r") as file:
                self.playlist = json.load(file)
        except(ValueError, FileNotFoundError):
            # Either file has a mistake in indentations, has been corrupted or didn't exist. Let's create a new one later
            with open(self.fPlaylist, "w") as file:
                json.dump(list(), file)
                self.playlist = list()

        # Get auth
        if self.config.useToken:
            self.flagUseToken = True
            self.userToken = self.config.token
        else:
            self.flagUseToken = False
            self.userName = self.config.email
            self.userPassword = self.config.password

        if not self.config.usePrefix:
            self.logger.info("usePrefix set to false in config, using defaults")
            self.prefix = None
            self.flagUsePrefix = False
        else:
            self.logger.info("usePrefix set to true in config, loaded {name} as prefix".format(name=self.config.prefix))
            self.prefix = self.config.prefix
            self.flagUsePrefix = True

        # Store this for later usage when returning usage messages
        self.formatPrefix = None
        
        # Vote lists and properties
        # Store also if we reach the point
        self.voteSkipList = list()
        self.voteSkip = False
        self.voteShuffleList = list()
        self.voteShuffle = False
        self.votePercentage = self.config.votePercentage
        
        self.player = None
        self.playerStartTime = None
        self.playerEndTime = None
        self.playerVolume = 1.0
        self.playerForceStop = False

        # Server related setup
        self.textChannelId = self.config.textChannel
        self.textChannel = None
        self.voiceChannelId = self.config.voiceChannel
        self.voiceChannel = None
        self.voiceClient = None
        self.logChannelId = None
        self.logChannel = None
        self.server = None
        
        self.admins = self.config.admin
        self.mods = self.config.mod

        self.embedColors = {"121546822765248512":int("0x0066BB", 0),"322455566675083274":int("0x0066BB", 0),"103215649530077184":int("0x10DF19", 0)}

        self.game = discord.Game(
            name = self.config.gameName,
            url = self.config.gameUrl,
            type = self.config.gameType)
        
        # Check if voting is enabled
        self.voteEnabled = self.config.voteEnabled
        if self.voteEnabled:
            self.voteSkipEnabled = self.config.voteSkipEnabled
            self.voteShuffleEnabled = self.config.voteShuffleEnabled
            if(self.voteSkipEnabled and self.voteShuffleEnabled):
                self.logger.info("Voting enabled")
            elif(self.voteSkipEnabled):
                self.logger.info("Skip vote only enabled")
            elif(self.voteShuffleEnabled):
                self.logger.info("Shuffle vote only enabled")
            self.votePercentage = self.config.votePercentage
            self.logger.info("Set vote requirement percentage to {percentage}%".format(percentage=int(self.votePercentage*100)))
        else:
            self.logger.info("Voting disabled")
            self.voteSkipEnabled = False
            self.voteShuffleEnabled = False
        
        # Gotta make sure we can add lists depending on config
        self.googleAPI = self.config.googleAPI
        if self.googleAPI:
            self.addPlaylist = self.config.addPlaylistEnabled
            self.youtube = Youtube(self.googleAPI)
            response = self.youtube.validate_key()
            if(response == False):
                self.youtube = None
        else:
            self.addPlaylist = False
            self.youtube = None

    async def on_ready(self):
        # Initialize login and states
        self.logger.info("Succesfully logged in as {name}".format(name=self.user.name))

        # We defined the discord.Game() class at the begin as self.game
        if(self.game.url and (self.game.type == 1)):
            self.logger.info("Started streaming {name}".format(name=self.game.name))
            await self.change_presence(game=self.game)
        else:
            self.logger.info("Started playing {name}".format(name=self.game.name))
            await self.change_presence(game=self.game)
        
        self.formatPrefix = self.user if not self.flagUsePrefix else self.prefix
        self.logger.info("Prefix set to \"{prefix}\"".format(prefix=self.formatPrefix))
        
        # We'll receive None if not found at self.get_channel()
        # We'll also receive an empty list at channelId when it's empty
        self.textChannel = list()
        for channelId in self.textChannelId:
            self.textChannel.append(self.get_channel(channelId))
        self.voiceChannel = self.get_channel(self.voiceChannelId)
        self.logChannel = self.get_channel(self.logChannelId)
        # Take server we got from first channel (this should be the main server)
        if(len(self.textChannel) > 0):
            self.server = self.textChannel[0].server
            if(self.server.me.nick):
                self.logger.info("Nickname \"{prefix}\" found".format(prefix=self.server.me.nick))
        else:
            self.logger.debug("Failed to retrieve main server, channel isn't defined in config")
            self.server = list(self.servers)[0]
            if(self.server.me.nick):
                self.logger.info("Nickname \"{prefix}\" found".format(prefix=self.server.me.nick))

        # Override elements in current playlist to support more info
        if(len(self.playlist) != 1):
            self.logger.info("Found {number} songs, loading...".format(number=len(self.playlist)))
        elif(len(self.playlist) == 1):
            self.logger.info("Found {number} song, loading...".format(number=len(self.playlist)))
        songList = list()
        playlist = self.playlist
        textLength = 0
        for pos, song in enumerate(self.playlist, start=1):
            user = await self.get_user_info(song[1])

            if(self.youtube):
                videoContent = self.youtube.getVideo(song[0])

                try:
                    if (videoContent["error"]["code"] == 403):
                        # Likely something with the key, revert to state without one
                        self.logger.exception("Youtube Data API returned 403 with the message: {message}".format(message=videoContent["error"]["message"]))
                        self.logger.debug("Falling back to defaults")
                        self.youtube = None
                    else:
                        continue
                except:
                    pass

                if(videoContent["pageInfo"]["totalResults"] == 0):
                    continue

                videoInfo = videoContent["items"][0]
                songList.append(Video(user, videoInfo["id"], title=videoInfo["snippet"]["title"], description=videoInfo["snippet"]["description"], duration=isodate.parse_duration(videoInfo["contentDetails"]["duration"]).seconds, views=videoInfo["statistics"]["viewCount"]))

                print(" "*textLength, end="\r")
                textPrint = "[{pos}/{len}] {name} - {url}".format(pos=pos, len=len(playlist), name=videoInfo["snippet"]["title"], url=videoInfo["id"])
                textLength = len(textPrint)
                try:
                    print(textPrint, end="\r")
                except:
                    print("", end="\r")
            else:
                songList.append(Video(user, song[0]))
            # Update this to current playlist
            self.playlist = songList
            
        await asyncio.sleep(1)
        print(" "*textLength, end="\r")
        self.logger.info("Done loading")
        self.voiceClient = await self.join_voice_channel(self.voiceChannel)
        if(len(self.admins) == 0):
            self.admins.append(self.server.owner)
            application = await self.application_info()
            if(self.server.owner != application.owner):
                self.admins.append(application.owner)
            

    async def on_message(self, message):
        # First check if it's us being tagged or correct prefix is being used
        if(self.flagUsePrefix == False):
            # Prevent issues, if this is smaller than 0 (wat?), we got a problem
            if(len(message.raw_mentions) == 0):
                return
            # It wasn't us who got tagged first, just ignore it I guess
            if(message.raw_mentions[0] != self.user.id):
                return
            # Check if the bot was tagged first, workaround method also for when a nick is used
            if not (message.content.startswith("<@{id}>".format(id=self.user.id)) or message.content.startswith("<@!{id}>".format(id=self.user.id))):
                return
        elif((self.flagUsePrefix == True) and (self.prefix != None)):
            if not message.content.startswith(self.prefix):
                return
        elif(message.author == self.user):
            # The bot shouldn't handle his own messages
            return
        else:
            # If neither of these match, propably something went wrong in the config
            self.logger.error("The prefix isn't configured correctly! Updating config to default mention")
            self.config.usePrefix = False
            self.flagUsePrefix = False
            self.config.update()
            try:
                if not self.prefix:
                    await self.send_message(message.channel, "Something went wrong, please try again using \n{prefix} {content}```".format(prefix=self.user.mention, content=message.content.split(' ', 1)[1]))
                else:
                    await self.send_message(message.channel, "Something went wrong, please try again using \n{prefix}{content}```".format(prefix=self.user.mention, content=message.content.split(' ', 1)[1]))
            except IndexError:
                await self.send_message(message.channel, "Something went wrong, please try again") 
            return

        # Remove first prefix or mention we checked
        try:
            # Credits to Plue for informing me about this method
            if not self.prefix:
                content = message.content.split(" ", 1)[1]
            else:
                content = message.content.replace(self.prefix, "", 1)
        except IndexError:
            return
            # In case we only mention the bot or use a prefix it can create exceptions

        # We want to make sure there's something after the add, it can't be empty right?
        if content.startswith("add"):
            if content.strip() == "add":
                self.logger.error("{user} ({id}: No arguments were passed after \"add\", aborting".format(user=message.author.name, id=message.author.id))
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} add <url / id>```".format(prefix=self.formatPrefix)))
                return

            content = content.replace("add ", "", 1)
            
            # Want to make sure we're getting the int as last
            try:
                int(content.split(' ', 1)[0])
                content = content.split(' ', 1)
                content.reverse()
                content = " ".join(content)
                self.logger.info("Reversing pos")
            except ValueError:
                pass
            
            # We got something prioritized, lets add some checks
            if (len(content.split(' ', 1)) == 2):
                if ((message.author in self.mods) or (message.author in self.admins)):
                    try:
                        queuePos = int(content.split(' ', 1)[1])-1
                        content = content.split(' ', 1)[0]
                    except:
                        queuePos = len(self.playlist)
                        content = content.split(' ', 1)[0]
                        await self.send_message(message.channel, "Failed to put song at given position \nUnknown number was given")
                else:
                    queuePos = len(self.playlist)
                    content = content.split(' ', 1)[0]
            else:
                queuePos = len(self.playlist)
            
            if(queuePos <= 0):
                queuePos = 0

            self.logger.info("Adding song at pos {pos}".format(pos=queuePos+1))

            songList = list()
            
            # Add support for complete playlists if we have the API
            # It could happen we had an shortened one so we can't take full link
            if(content.startswith("https://www.youtu") or content.startswith("http://www.youtu") or content.startswith("www.youtu")):
                self.logger.info("Received link: \"{link}\", parsing".format(link=content))
                # We declared youtube class at __init__, let's call it to parse
                url = self.youtube.parse(content)
                if(url["typeUrl"] == "video"):
                    self.logger.info("Received video with id \"{id}\"".format(id=url["url"]))
                    videoList.append(url["url"])
                elif(url["typeUrl"] == "list"):
                    self.logger.info("Received list with id \"{id}\"".format(id=url["url"]))
            else:
                url = {"url":content,"typeUrl":"video"}

            if self.youtube:
                if(url["typeUrl"] == "list"):
                    response = self.youtube.getList(url["url"])
                    if "error" in response.keys():
                        await self.send_message(message.channel, "Something went wrong during retrieving the playlist \nReceived the following response: \n```{message}```".format(message=content["error"]["message"]))
                        return

                    # Received the content from the API, parse it for the id's
                    for video in response["items"]:
                        videoContent = self.youtube.getVideo(video)
                    
                        # We received nothing about this, abort this one
                        if(videoContent["pageInfo"]["totalResults"] == 0):
                            self.logger.info("Found nothing, aborting")
                            continue
                        videoInfo = videoContent["items"][0]
                        self.logger.info("Added {title} ({id})".format(title=videoInfo["snippet"]["title"], id=videoInfo["id"]))
                        songList.append(Video(message.author, videoInfo["id"], title=videoInfo["snippet"]["title"], description=videoInfo["snippet"]["description"], duration=isodate.parse_duration(videoInfo["contentDetails"]["duration"]).seconds, views=videoInfo["statistics"]["viewCount"]))
                elif(url["typeUrl"] == "video"):
                    videoContent = self.youtube.getVideo(url["url"])
                    
                    # We received nothing about this, abort this one
                    if(videoContent["pageInfo"]["totalResults"] == 0):
                        self.logger.info("Found nothing, aborting")
                        return
                    videoInfo = videoContent["items"][0]
                    self.logger.info("Added {title} ({id})".format(title=videoInfo["snippet"]["title"], id=videoInfo["id"]))
                    songList.append(Video(message.author, videoInfo["id"], title=videoInfo["snippet"]["title"], description=videoInfo["snippet"]["description"], duration=isodate.parse_duration(videoInfo["contentDetails"]["duration"]).seconds, views=videoInfo["statistics"]["viewCount"]))
            else:
                if(url["typeUrl"] == "list"):
                    self.send_message(message.channel, "List adding is disabled \nPlease contact the host if looking to enable this")
                    return
                elif(url["typeUrl"] == "video"):
                    self.logger.info("Added {url}".format(url=url["content"]))
                    songList.append(Video(message.author, url["content"]))
            
            # Make the current song a "earlier" element in the list (current playing song "doesn't count")
            if(not self.player):
                queuePos += 1
            # Easy method to parse multiple songs in case, not efficient for 1 only though
            embed = discord.Embed()
            embed.set_author(name=self.user, icon_url=self.user.avatar_url, url=embed.Empty)
            if self.user.id in self.embedColors.keys():
                embed.color = self.embedColors[self.user.id]
            embed.title = embed.Empty
            embed.url = embed.Empty
            messageDescription = list()
            
            for queuePos, song in enumerate(songList, start=queuePos):
                self.playlist.insert(queuePos+songList.index(song), song)
                if(len(songList) == 1):
                    if(song.title):
                        messageDescription.append("Added **[{title}](https://www.youtube.com/watch?v={url} '{url}')** at position {pos}".format(title=song.title, url=song.url, pos=queuePos))
                    else:
                        messageDescription.append("Added **[https://www.youtube.com/watch?v={url}](https://www.youtube.com/watch?v={url} '{url}')** at position {pos}".format(url=song.url, pos=queuePos))
                else:
                    if(songList.index(song) == 0):
                        messageDescription.append("Added: \n")
                    if(songList.index(song) < 20):
                        messageDescription.append("**[{pos}/{total}] [{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(pos=queuePos, total=len(songList), title=song.title, url=song.url))

            embed.description = "\n".join(messageDescription)
            await self.send_message(message.channel, embed=embed)
                                                

            # Update playlist file to current playlist (not efficient but we need the complete playlist)
            songList = list()
            for song in self.playlist:
                songList.append([song.url, song.user.id])
            with open(self.fPlaylist, "w", encoding="utf-8") as file:
                json.dump(songList, file)

        if content.startswith("play"):
            if content.strip() != "play":
                return

            if len(self.playlist) == 0:
                await self.send_message(message.channel, "Playlist is empty")
                return
            if self.is_voice_connected(self.server):
                if(self.voiceClient.channel != self.voiceChannel):
                    return
                if(self.player):
                    await self.send_message(message.channel, "The player is already active {author} !\nJoin `{voice}` channel to tune in".format(author=message.author.mention, voice=self.voiceChannel.name))
                    return
                while(len(self.playlist) > 0):
                    # Some bizarre bug makes this continue so stop this loop
                    if((len(self.playlist) == 0) or self.playerForceStop):
                        break
                    # Reserve the attrib to prevent double players while waiting
                    self.player = str()
                    # We've got an Video object with more attribs if API was used
                    if(self.playlist[0].title != None):
                        self.logger.debug("{author} ({id}): Preparing {song} (\"{url}\", \"{duration}\"))".format(author=self.playlist[0].user.name, id=self.playlist[0].user.id, song=self.playlist[0].title, url=self.playlist[0].url, duration=self.playlist[0].duration))
                    else:
                        self.logger.debug("{author} ({id}): Preparing song (\"{url}\")".format(author=self.playlist[0].user.name, id=self.playlist[0].user.id, url=self.playlist[0].url))
                    self.voteSkip = False
                    self.voteShuffle = False
                    try:
                        self.player = await self.voiceClient.create_ytdl_player(self.playlist[0].url)
                    except(youtube_dl.utils.GeoRestrictedError, youtube_dl.utils.DownloadError):
                        self.logger.error("Youtube-dl failed to download from \"{url}\"".format(url=self.playlist[0].url))
                        del self.playlist[0]
                        songList = list()
                        for song in self.playlist:
                            songList.append([song.url, song.user.id])
                        with open(self.fPlaylist, "w", encoding="utf-8") as file:
                            json.dump(songList, file)
                        continue
                    # Based on Discord.py API we should receive None when youtube-dl fails to extract info
                    if((self.player.title == None) or (self.player.error)):
                        self.logger.error("Youtube-dl failed to extract info from \"{url}\"".format(url=self.playlist[0].url))
                        del self.playlist[0]
                        continue
                    self.player.volume = self.playerVolume
                    if(self.playlist[0].title != None):
                        self.game = discord.Game(
                            name = self.playlist[0].title,
                            url = self.config.gameUrl,
                            type = 1)
                    else:
                        self.game = discord.Game(
                            name = self.player.title,
                            url = self.config.gameUrl,
                            type = 1)
                    await self.change_presence(game=self.game)
                    self.player.start()

                    embed = discord.Embed()
                    embed.set_author(name=self.playlist[0].user, icon_url=self.playlist[0].user.avatar_url, url=embed.Empty)
                    if self.playlist[0].user.id in self.embedColors.keys():
                        embed.color = self.embedColors[self.playlist[0].user.id]
                    embed.title = embed.Empty
                    embed.url = embed.Empty
                    if (self.playlist[0].title != None):
                        embed.description = "Started playing **[{title}](https://www.youtube.com/watch?v={url} '{url}')** \nDuration: {duration} \n{views} views".format(title=self.playlist[0].title, url=self.playlist[0].url, duration=self.playlist[0].duration, views=self.playlist[0].views)
                        embed.add_field(name="Description", value=self.playlist[0].description)
                    else:
                        embed.description = "Started playing **[{title}](https://www.youtube.com/watch?v={url} '{url}')** \nDuration: {duration}".format(title=self.player.title, url=self.player.url, duration=str(datetime.timedelta(seconds=self.player.duration)))
                    try:
                        await self.send_message(message.channel, embed=embed)
                    except discord.errors.HTTPException:
                        embed.remove_field(0)
                        await self.send_message(message.channel, embed=embed)
                    # Keep checking if something happened with the votes
                    while(self.player.is_playing() or (not self.player.is_done())):
                        await asyncio.sleep(1)
                        if(self.voteShuffle):
                            if(len(self.playlist) > 2):
                                # We want to make sure we're not going to repeat our current song
                                song = self.playlist[0]
                                del self.playlist[0]
                                random.shuffle(self.playlist)
                                self.playlist.insert(0, song)
                                self.voteShuffleList = list()
                                self.voteShuffle = False
                                embed = discord.Embed()
                                embed.set_author(name=self.user, icon_url=self.user.avatar_url, url=embed.Empty)
                                if self.user.id in self.embedColors.keys():
                                    embed.color = self.embedColors[self.user.id]
                                embed.title = "Voting"
                                embed.url = embed.Empty
                                embed.description = "Shuffling playlist"
                                await self.send_message(message.channel, embed=embed)
                            else:
                                self.voteShuffleList = list()
                                self.voteShuffle = False
                                embed = discord.Embed()
                                embed.set_author(name=self.user, icon_url=self.user.avatar_url, url=embed.Empty)
                                if self.user.id in self.embedColors.keys():
                                    embed.color = self.embedColors[self.user.id]
                                embed.title = "**Voting**"
                                embed.url = embed.Empty
                                embed.description = "Playlist is too short to shuffle!"
                                await self.send_message(message.channel, embed=embed)
                        if(self.voteSkip):
                            self.voteSkipList = list()
                            self.voteSkip = False
                            embed = discord.Embed()
                            embed.set_author(name=self.user, icon_url=self.user.avatar_url, url=embed.Empty)
                            if self.user.id in self.embedColors.keys():
                                embed.color = self.embedColors[self.user.id]
                            embed.title = "**Voting**"
                            embed.url = embed.Empty
                            embed.description = "Skipping **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(title=self.playlist[0].title, url=self.playlist[0].url)
                            await self.send_message(message.channel, embed=embed)
                            self.player.stop()

                    if self.player.error:
                        embed = discord.Embed()
                        embed.set_author(name=self.user, icon_url=self.user.avatar_url, url=embed.Empty)
                        if self.user.id in self.embedColors.keys():
                            embed.color = self.embedColors[self.user.id]
                        embed.title = embed.Empty
                        embed.url = embed.Empty
                        embed.description = "Player stopped with the following message: \n```{message}```".format(message-self.player.error)
                        await self.send_message(message.channel, embed=embed)

                    self.voteSkipList = list()
                    self.voteSkip = False
                    del self.playlist[0]

                    songList = list()
                    for song in self.playlist:
                        songList.append([song.url, song.user.id])
                    with open(self.fPlaylist, "w", encoding="utf-8") as file:
                        json.dump(songList, file)

                # Reset the game
                self.game = discord.Game(
                    name = self.config.gameName,
                    url = self.config.gameUrl,
                    type = self.config.gameType)

                await self.change_presence(game=self.game)
                self.player = None
                self.playerForceStop = False
        
        if content.startswith("search"):
            if content.strip() == "search":
                self.logger.error("No arguments were passed after \"search\", aborting")
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} search <keywords>```".format(prefix=self.formatPrefix)))
                return

            if(not self.youtube):
                return

            content = content.replace("search ", "", 1)

            result = self.youtube.search(content)
            embed = discord.Embed()
            embed.set_author(name=message.author, icon_url=message.author.avatar_url, url=embed.Empty)
            if message.author.id in self.embedColors.keys():
                embed.color = self.embedColors[message.author.id]
            embed.title = embed.Empty
            embed.url = embed.Empty
            embed.description = embed.Empty
            videoList = list()
            for pos, video in enumerate(result["items"], start=1):
                videoList.append("[{pos}/{total}] - **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(pos=pos, total=len(result["items"]), title=video["snippet"]["title"], url=video["id"]["videoId"]))
            embed.add_field(name="**Search**:", value="\n".join(videoList))
            searchMessage = await self.send_message(message.channel, embed=embed)
            for pos in range(0, (len(videoList)+1)):
                if(pos == 1):
                    await self.add_reaction(searchMessage, "1\u20e3")
                elif(pos == 2):
                    await self.add_reaction(searchMessage, "2\u20e3")
                elif(pos == 3):
                    await self.add_reaction(searchMessage, "3\u20e3")
                elif(pos == 4):
                    await self.add_reaction(searchMessage, "4\u20e3")
                elif(pos == 5):
                    await self.add_reaction(searchMessage, "5\u20e3")
            res = await self.wait_for_reaction(["1\u20e3", "2\u20e3", "3\u20e3", "4\u20e3", "5\u20e3"], message=searchMessage, timeout=20.0, user=message.author)
            if(res):
                if(res.reaction.emoji == "1\u20e3"):
                    number = 0
                elif(res.reaction.emoji == "2\u20e3"):
                    number = 1
                elif(res.reaction.emoji == "3\u20e3"):
                    number = 2
                elif(res.reaction.emoji == "4\u20e3"):
                    number = 3
                elif(res.reaction.emoji == "5\u20e3"):
                    number = 4

                await self.clear_reactions(searchMessage)

                videoContent = self.youtube.getVideo(result["items"][number]["id"]["videoId"])
                    
                # We received nothing about this, abort this one
                if(videoContent["pageInfo"]["totalResults"] == 0):
                    self.logger.info("Found nothing, aborting")
                    return
                videoInfo = videoContent["items"][0]
                self.logger.info("Added {title} ({id})".format(title=videoInfo["snippet"]["title"], id=videoInfo["id"]))
                video = Video(message.author, videoInfo["id"], title=videoInfo["snippet"]["title"], description=videoInfo["snippet"]["description"], duration=isodate.parse_duration(videoInfo["contentDetails"]["duration"]).seconds, views=videoInfo["statistics"]["viewCount"])
                self.playlist.append(video)
                embed = discord.Embed()
                embed.set_author(name=message.author, icon_url=message.author.avatar_url, url=embed.Empty)
                if message.author.id in self.embedColors.keys():
                    embed.color = self.embedColors[message.author.id]
                embed.title = embed.Empty
                embed.url = embed.Empty
                embed.description = "Added **[{title}](https://www.youtube.com/watch?v={url} '{url}')** at position {pos}".format(title=video.title, url=video.url, pos=len(self.playlist))
                await self.send_message(message.channel, embed=embed)

                # Update playlist file to current playlist (not efficient but we need the complete playlist)
                songList = list()
                for song in self.playlist:
                    songList.append([song.url, song.user.id])
                with open(self.fPlaylist, "w", encoding="utf-8") as file:
                    json.dump(songList, file)
        
        if content.startswith("pause"):
            if not self.player:
                await self.send_message(message.channel, "Player isn't active")
                return
            self.player.pause()
            embed = discord.Embed()
            embed.set_author(name=message.author, icon_url=message.author.avatar_url, url=embed.Empty)
            if message.author.id in self.embedColors.keys():
                embed.color = self.embedColors[message.author.id]
            embed.title = embed.Empty
            embed.url = embed.Empty
            embed.description = "Paused **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(title=self.playlist[0].title, url=self.playlist[0].url)
            await self.send_message(message.channel, embed=embed)
            if(self.playlist[0].title != None):
                self.game = discord.Game(
                    name = "{song} (paused)".format(song=self.playlist[0].title),
                    url = self.config.gameUrl,
                    type = 1)
            else:
                self.game = discord.Game(
                    name = "{song} (paused)".format(song=self.player.title),
                    url = self.config.gameUrl,
                    type = 1)
            await self.change_presence(game=self.game)

        if content.startswith("resume"):
            if not self.player:
                await self.send_message(message.channel, "Player isn't active")
                return
            self.player.resume()
            embed = discord.Embed()
            embed.set_author(name=message.author, icon_url=message.author.avatar_url, url=embed.Empty)
            if message.author.id in self.embedColors.keys():
                embed.color = self.embedColors[message.author.id]
            embed.title = embed.Empty
            embed.url = embed.Empty
            embed.description = "Resumed **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(title=self.playlist[0].title, url=self.playlist[0].url)
            await self.send_message(message.channel, embed=embed)
            if(self.playlist[0].title != None):
                self.game = discord.Game(
                    name = self.playlist[0].title,
                    url = self.config.gameUrl,
                    type = 1)
            else:
                self.game = discord.Game(
                    name = self.player.title,
                    url = self.config.gameUrl,
                    type = 1)
            await self.change_presence(game=self.game)
        
        if content.startswith("stop"):
            if not self.player:
                await self.send_message(message.channel, "Player isn't active")
                return

            if(self.playerForceStop):
                return
            
            self.playerForceStop = True
            embed = discord.Embed()
            embed.set_author(name=message.author, icon_url=message.author.avatar_url, url=embed.Empty)
            if message.author.id in self.embedColors.keys():
                embed.color = self.embedColors[message.author.id]
            embed.title = embed.Empty
            embed.url = embed.Empty
            embed.description = "Stopping player after **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(title=self.playlist[0].title, url=self.playlist[0].url)
            await self.send_message(message.channel, embed=embed)

        if content.startswith("clear"):
            pass

        if content.startswith("skip"):
            if not self.player:
                await self.send_message(message.channel, "Player isn't active")
                return

            if content.strip() != "skip":
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} skip```".format(prefix=self.formatPrefix)))
                return

            if(message.author not in self.voteSkipList):
                self.voteSkipList.append(message.author)

            voiceMembers = self.updateVoteState()

            embed = discord.Embed()
            embed.set_author(name=message.author, icon_url=message.author.avatar_url, url=embed.Empty)
            if message.author.id in self.embedColors.keys():
                embed.color = self.embedColors[message.author.id]
            embed.title = "**Voting**"
            embed.url = embed.Empty
            if((math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteSkipList)) > 1):
                embed.description = "{author} has voted to skip \n{votes} more votes needed".format(author=message.author.name, votes=(math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteSkipList)))
            elif((math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteSkipList)) == 1):
                embed.description = "{author} has voted to skip \n{votes} more vote needed".format(author=message.author.name, votes=(math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteSkipList)))
            else:
                embed.description = "{author} has voted to skip \n{votes} more votes needed".format(author=message.author.name, votes="No")
            await self.send_message(message.channel, embed=embed)

        if content.startswith("shuffle"):
            if not self.player:
                await self.send_message(message.channel, "Player isn't active")
                return

            if content.strip() != "shuffle":
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} shuffle```".format(prefix=self.formatPrefix)))
                return

            if(message.author not in self.voteShuffleList):
                self.voteShuffleList.append(message.author)

            voiceMembers = self.updateVoteState()

            embed = discord.Embed()
            embed.set_author(name=message.author.id, icon_url=message.author.avatar_url, url=embed.Empty)
            if message.author.id in self.embedColors.keys():
                embed.color = self.embedColors[message.author.id]
            embed.title = "**Voting**"
            embed.url = embed.Empty
            if((math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteShuffleList)) > 1):
                embed.description = "{author} has voted to shuffle the playlist \n{votes} more votes needed".format(author=message.author.name, votes=(math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteShuffleList)))
            if((math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteShuffleList)) == 1):
                embed.description = "{author} has voted to shuffle the playlist \n{votes} more vote needed".format(author=message.author.name, votes=(math.ceil(len(voiceMembers)*self.votePercentage)-len(self.voteShuffleList)))
            else:
                embed.description = "{author} has voted to shuffle the playlist \n{votes} more votes needed".format(author=message.author.name, votes="No")
            
            await self.send_message(message.channel, embed=embed)

        if content.startswith("volume"):
            if not self.player:
                await self.send_message(message.channel, "Player isn't active")
                return

            if content.strip() == "volume":
                self.logger.error("No arguments were passed after \"volume\", aborting")
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} volume <0-10>```".format(prefix=self.formatPrefix)))
                return

            content = content.replace("volume ", "", 1)
            
            embed = discord.Embed()
            embed.title = embed.Empty
            embed.url = embed.Empty
            embed.set_author(name=message.author.name, icon_url=message.author.avatar_url, url=embed.Empty)
            
            try:
                content = float(content)
                if(content > 10):
                    content = 10.0
                if(content < 0):
                    content = 0.0
                self.playerVolume = content/5
                if(self.player and (self.player != str())):
                    self.player.volume = content/5
                embed.description = "Volume set to `{value}`".format(value=content)
                await self.send_message(message.channel, embed=embed)
            except ValueError:
                self.logger.error("Invalid arguments were passed after \"volume\", aborting")
                embed.description = formatErrorSyntax.format(format="```{prefix} volume <0-10>```".format(prefix=self.formatPrefix))
                await self.send_message(message.channel, embed=embed)
                return

        if content.startswith("timeleft"):
            if not self.player:
                await self.send_message(message.channel, "Player isn't active")
                return

            if self.player.is_done():
                await self.send_message(message.channel, "The player is done")
                return

            if content.strip() != "timeleft":
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} timeleft```".format(prefix=self.formatPrefix)))
                return

            return
            # Add more code

        if content.startswith("list"):
            if content.strip() != "list":
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} list```".format(prefix=self.formatPrefix)))
                return

            embed = discord.Embed()
            if(len(self.playlist) > 0):
                embed.set_author(name=self.playlist[0].user, icon_url=self.playlist[0].user.avatar_url, url=embed.Empty)
            else:
                embed.set_author(name=message.author, icon_url=message.author.avatar_url, url=embed.Empty)
            if self.user.id in self.embedColors.keys():
                embed.color = self.embedColors[self.user.id]
            embed.title = embed.Empty
            embed.url = embed.Empty

            songList = list()
            remaining = 0
            for queuePos, song in enumerate(self.playlist, start=1):
                if self.player:
                    if queuePos == 1:
                        embed.description = "Currently playing: **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(title=self.playlist[0].title, url=self.playlist[0].url)
                        continue
                    songList.append("[{pos}/{total}] - **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(pos=(queuePos-1), total=(len(self.playlist)-1), title=song.title, url=song.url))
                else:
                    songList.append("[{pos}/{total}] - **[{title}](https://www.youtube.com/watch?v={url} '{url}')**".format(pos=queuePos, total=(len(self.playlist)), title=song.title, url=song.url))
            
            if(len(songList) >= 8):
                embed.add_field(name="**Playlist**:", value="\n".join(songList[0:7]))
            else:
                embed.add_field(name="**Playlist**:", value="\n".join(songList[0:(len(songList)-1)]))

            await self.send_message(message.channel, embed=embed)

        if content.startswith("eval"):
            if content.strip() == "eval":
                self.logger.error("No arguments were passed after \"eval\", aborting")
                await self.send_message(message.channel, formatErrorSyntax.format(format="```{prefix} eval <value>```".format(prefix=self.formatPrefix)))
                return

            content = content.replace("eval ", "", 1)
            # Censor private info from anyone
            censored = ["self.email", "self.password", "self.token", "self.config.email", "self.config.password", "self.config.token", "self.googleAPI", "self.config.googleAPI"]
            if any(word in content for word in censored):
                await self.send_message(message.channel, "`Censored due to private info`")
                return
            try:
                output = eval(content)
                await self.send_message(message.channel, "```{output}```".format(output=output))
            except:
                self.logger.error(traceback.format_exc())
                await self.send_message(message.channel, "```{error}```".format(error=traceback.format_exc()))

        if(content.startswith("exit") or content.startswith("shutdown")):
            self.logger.info("Shutting down")
            await self.logout()

    async def on_voice_state_update(self, memberBefore, memberAfter):
        # Don't process if we don't got a voicechannel
        if not self.voiceChannel:
            return

        # Process voicestate updates from clients connected to voicechannel
        flUpdateVoteState = False
        # await self.checkVoiceClient()
        if((memberBefore.voice.voice_channel != self.voiceChannel) or (memberAfter.voice.voice_channel != self.voiceChannel)):
            return
            # We don't want to parse voicechannel info which doesn't involve us
        if(memberAfter.voice.voice_channel == None):
            if(memberAfter.id in self.voteSkipList):
                self.voteSkipList.remove(memberAfter.id)
                # Return channel he disconnected from, he has to have a voicechannel before he disconnected at memberBefore
                self.logger.info("{user} ({userid}) disconnected from {channel} ({channelid}), removing from skip vote".format(user=memberAfter.name, userid=memberAfter.id, channel=memberBefore.voice.voice_channel.name, channelid=memberBefore.voice.voice_channel.id))
                updateVoteState = True
            if(memberAfter.id in self.voteShuffleList):
                self.voteShuffleList.remove(memberAfter.id)
                self.logger.info("{user} disconnected from {channel} ({channelid}), removing from shuffle/scramble vote".format(user=memberAfter.name, userid=memberAfter.id, channel=memberBefore.voice.voice_channel.name, channelid=memberBefore.voice.voice_channel.id))
                self.updateVoteState()
            # Nothing to do here, let's terminate
            return
        if(memberAfter.voice.deaf or memberAfter.voice.self_deaf):
            if(memberAfter.id in self.voteSkipList):
                self.voteSkipList.remove(memberAfter.id)
                # Return channel he disconnected from, he has to have a voicechannel before he disconnected at memberBefore
                self.logger.info("{user} ({userid}) deafened at {channel} ({channelid}), removing from skip vote".format(user=memberAfter.name, userid=memberAfter.id, channel=memberBefore.voice.voice_channel.name, channelid=memberBefore.voice.voice_channel.id))
                flUpdateVoteState = True
            if(memberAfter.id in self.voteShuffleList):
                self.voteShuffleList.remove(memberAfter.id)
                self.logger.info("{user} ({userid}) deafened at {channel} ({channelid}), removing from shuffle/scramble vote".format(user=memberAfter.name, userid=memberAfter.id, channel=memberBefore.voice.voice_channel.name, channelid=memberBefore.voice.voice_channel.id))
                flUpdateVoteState = True
            # Nothing to do here, let's terminate after checking the votes
            if flUpdateVoteState:
                self.updateVoteState()
            return

    def updateVoteState(self):
        if self.is_voice_connected(self.server):
            if(self.voiceClient.channel == self.voiceChannel):
                voiceMembers = list()
                # Check if 75% of the voice members matching the criteria has voted
                for member in self.voiceChannel.voice_members:
                    if member == self.user:
                        continue
                    if (member.voice.deaf or member.voice.self_deaf):
                        continue
                    voiceMembers.append(member)
                if(((len(self.voteSkipList)/len(voiceMembers)) >= self.votePercentage) and self.voteSkipEnabled):
                    self.voteSkip = True
                if(((len(self.voteShuffleList)/len(voiceMembers)) >= self.votePercentage) and self.voteShuffleEnabled):
                    self.voteShuffle = True
                return voiceMembers
    
    def checkVoiceClient(self):
        if(len(self.voiceChannel.voice_members) >= 1):
            if self.voiceClient:
                if(self.voiceClient.channel == self.voiceChannel):
                    if(len(self.voiceChannel.voice_members) >= 2):
                        return
                    return None
                else:
                    return False
            else:
                return True

    async def on_server_join(self, server):
        if(self.textChannel == None):
            #await self.send_message(server.owner, "<text about configuring music channel>")
            flagPass = False
            while(flagPass == False):
                message = await self.wait_for_message(timeout=180.0, author=server.owner)
                if not message:
                    continue
                if(len(message.raw_channel_mentions) >= 1):
                    channel = server.get_channel(message.raw_channel_mentions[0])
                    if channel.type == discord.ChannelType.text:
                        self.textChannel = channel
                        break
            

    def run(self):
        self.logger.info("Logging in")
        # No comment needed to explain this
        if(self.flagUseToken):
            if(self.userToken == None):
                self.logger.critical("Token isn't defined, aborting")
                return
            super().run(self.userToken)
        else:
            if((self.userName == None) or (self.userPassword == None)):
                self.logger.critical("Login credentials aren't defined, aborting")
                return
            super().run(self.userName,self.userPassword)

class Youtube:
    def __init__(self, key=None):
        self.key = key
        apiBase = "https://www.googleapis.com/"
        apiYoutube = apiBase+"youtube/v3/"
        self.apiYoutubeVideos = apiYoutube+"videos?key={key}&part=snippet,contentDetails,status,statistics&id={id}"
        self.apiYoutubeVideoSearch = apiYoutube+"search?key={key}&part=snippet&type=video&q={searchQuery}"
        self.apiYoutubeLists = apiYoutube+"playlistItems?key={key}&part=snippet,contentDetails&maxResults=50&playlistId={id}"

        self.logger = logging.getLogger(self.__class__.__name__)
        
    def getList(self, playlist):
        request = requests.get(self.apiYoutubeLists.format(key=self.key, id=playlist))
        return request.json()
    
    def getVideo(self, video):
        request = requests.get(self.apiYoutubeVideos.format(key=self.key, id=video))
        return request.json()

    def parse(self, url):
        # Use this if we get a https://www.youtube.com/ link
        url_data = urllib.parse.urlparse(url)
        data = urllib.parse.parse_qs(url_data.query)
        try:
            return {"url":data["list"][0],"typeUrl":"list"}
        except (ValueError, KeyError):
            return {"url":data["v"][0],"typeUrl":"video"}
        except:
            return {"url":None, "typeUrl":None}

    def validate_key(self):
        request = requests.get(self.apiYoutubeVideos.format(key=self.key, id="_1RYCUPKhy8"))
        content = request.json()
        error = content.get("error")
        if(error != None):
            errors = error.get("errors")
            if(errors != None):
                errors = errors[0]
                if(errors["reason"] == "keyInvalid"):
                    self.logger.warning("Received invalid key, disabling Youtube API")
                    return False
            else:
                if(error["code"] == 400):
                    self.logger.warning("Received response 400, disabling Youtube API")
                    self.key = None
                    return False
        else:
            return True

    def search(self, query):
        request = requests.get(self.apiYoutubeVideoSearch.format(key=self.key, searchQuery=query))
        return request.json()
        

# Storing info from videos
class Video:
    def __init__(self, user, url, title=None, description=None, duration=None, views=None):
        self._user = user
        self._url = url
        self._title = title
        self._description = description
        self._duration = duration
        self._views = views

    # Return other formats when calling main values
    @property
    def user(self):
        return self._user
    
    @property
    def url(self):
        return self._url
    
    @property
    def title(self):
        return self._title
    
    @property
    def description(self):
        return self._description
    
    @property
    def duration(self):
        return str(datetime.timedelta(seconds=self._duration))
    
    @property
    def views(self):
        # Add some numbers so we can reverse properly
        viewCount = str(self._views) + "001"
        viewCount = viewCount[::-1]
        viewCount = ".".join([viewCount[i:i+3] for i in range(0, len(viewCount), 3)])
        viewCount = viewCount[::-1]
        viewCount = viewCount[0:(len(viewCount)-3)]
        if viewCount.endswith("."):
            viewCount = viewCount[0:(len(viewCount)-1)]
        return viewCount

class Config:
    def __init__(self, file):
        self.file = file
    
        # Add logging
        self.logger = logging.getLogger(self.__class__.__name__)

        # Add check for existence of file, if not, make one
        if not os.path.exists(self.file):
            self.reset()

        # Read the config for vars
        config = configparser.ConfigParser()
        config.read(self.file, encoding="utf-8")
        
        # Parse all vars
        self.useToken = config.getboolean("Auth", "useToken", fallback=True)

        # Load them early to prevent exceptions when updating
        self.token = config.get("Auth", "token", fallback=None)
        self.email = config.get("Auth", "email", fallback=None)
        self.password = config.get("Auth", "password", fallback=None)

        if not self.useToken:
            self.logger.info("Token usage is set to false")
            self.logger.info("Loading e-mail and password")

            # Fallback to None if it's empty, configparser doesn't support None
            if self.email == "":
                self.email = None
            
            if self.password == "":
                self.password = None

            if not (self.email and self.password):
                if not self.email:
                    self.logger.critical("E-mail isn't configurated in the config")
                if not self.password:
                    self.logger.critical("Password isn't configurated in the config")
                self.logger.critical("Logging in won't work, improper login credentials has been passed!")
        else:
            self.logger.info("Token usage is set to true")
            self.logger.info("Loading token")

            if self.token == "":
                self.token = False
            if not self.token:
                self.logger.critical("Bot token isn't configurated in the config")
                self.logger.critical("Logging in won't work, improper login credentials has been passed!")

        # Load admins and mods for command access
        # Add level access?
        self.logger.info("Loading admins")
        self.admin = config.get("Administration", "Administrator", fallback=None)
        if self.admin == "":
            self.admin = list()
        if self.admin:
            self.admin = self.admin.split(",")
            if len(self.admin) != 1:
                self.logger.info("Loaded {amount} admins".format(amount=len(self.admin)))
            else:
                self.logger.info("Loaded {amount} admin".format(amount=len(self.admin)))
        else:
            self.logger.warning("An administrator isn't configured, bot will default to server owner when joining")

        self.logger.info("Loading mods")
        self.mod = config.get("Administration", "Moderator", fallback=None)
        if self.mod == "":
            self.mod = list()
        if self.mod:
            self.mod = self.mod.split(",")
            if len(self.mod) != 1:
                self.logger.info("Loaded {amount} mods".format(amount=len(self.mod)))
            else:
                self.logger.info("Loaded {amount} mod".format(amount=len(self.mod)))
        else:
            if self.admin:
                self.logger.warning("An moderator isn't configured, access is available to admin only")

        # Load Google API
        self.logger.info("Loading Google API token")
        self.googleAPI = config.get("Administration", "googleAPI", fallback=None)
        if self.googleAPI == "":
            self.googleAPI = None
        if not self.googleAPI:
           self.logger.warning("Google API key isn't configured, some features will not work as intended")

        # Define channels we can use as bot
        # If someone improperly configurated a channel, we'll split and take first as default
        self.textChannel = config.get("Administration", "textChannel", fallback=None)
        if self.textChannel == "":
            self.textChannel = list()
        if self.textChannel:
            self.textChannel = self.textChannel.split(",")

        self.voiceChannel = config.get("Administration", "voiceChannel", fallback=None)
        if self.voiceChannel == "":
            self.voiceChannel = None
        if self.voiceChannel:
            # Make sure we got only the first element
            self.voiceChannel = self.voiceChannel.split(",")
            self.voiceChannel = self.voiceChannel[0]
        
        self.logChannel = config.get("Administration", "logChannel", fallback=None)
        if self.logChannel == "":
            self.logChannel = None
        if self.logChannel:
            self.logChannel = self.logChannel.split(",")
            self.logChannel = self.logChannel[0]

        # Use by default not a custom prefix, if true, use the configured one
        self.usePrefix = config.getboolean("Administration", "usePrefix", fallback=False)
        self.prefix = config.get("Administration", "prefix", fallback=None)

        if self.usePrefix == "":
            self.usePrefix = False
        if not self.usePrefix:
            self.logger.info("Prefix usage is set to false")
            self.logger.info("Configuring bot mention as prefix on login")
        else:
            self.logger.info("Prefix usage is set to true")
            self.logger.info("Loading prefix")
            if not self.prefix:
                self.logger.warning("Prefix isn't configured, configuring bot mention as prefix on login")
                self.usePrefix = False
            else:
                self.logger.info("Prefix set to \"{prefix}\"".format(prefix=self.prefix))

        # Load a game which the bot seems to play
        self.gameName = config.get("Bot", "gameName", fallback=None)
        self.gameUrl = config.get("Bot", "gameUrl", fallback=None)
        self.gameType = config.getint("Bot", "gameType", fallback=None)
        if self.gameName == "":
            self.gameName = None
        if self.gameName:
            if self.gameUrl == "":
                self.gameUrl = None
            if(self.gameUrl and (self.gameType == 1)):
                self.logger.info("Loaded stream \"{name}\"".format(name=self.gameName))
            else:
                self.logger.info("Loaded game \"{name}\"".format(name=self.gameName))

        self.voteEnabled = config.getboolean("Voting", "voteEnabled", fallback=True)
        self.voteSkipEnabled = config.getboolean("Voting", "voteSkipEnabled", fallback=True)
        self.voteShuffleEnabled = config.getboolean("Voting", "voteShuffleEnabled", fallback=True)
        self.votePercentage = config.getfloat("Voting", "votePercentage", fallback=0.75)
        
        # Hidden option, lets keep it that
        self.addPlaylistEnabled = config.getboolean("Youtube", "addPlaylistEnabled", fallback=True)

        # Just make sure the config isn't missing any sections
        Config.update(self)

    def reset(self):
        config = configparser.ConfigParser(allow_no_value=True)

        self.logger.warning("Resetting the config to default values")
        # Set auth section up with no values (done)
        config.add_section("Auth")
        config.set("Auth", "useToken", "false")
        config.set("Auth", "token", "")
        config.set("Auth", "email", "")
        config.set("Auth", "password", "")
        config.set("Auth", "")

        config.add_section("Administration")
        config.set("Administration", "; Split admins/mods using \",\" don't use spaces. To grant access use the id of the user you wish to add.")
        config.set("Administration", "Administrator", "")
        config.set("Administration", "Moderator", "")
        config.set("Administration", "")
        config.set("Administration", "googleAPI", "")
        config.set("Administration", "textChannel", "")
        config.set("Administration", "voiceChannel", "")
        try:
            if self.logChannel:
                config.set("Administration", "logChannel", "")
        except AttributeError:
            pass
        config.set("Administration", "usePrefix", "false")
        config.set("Administration", "prefix", "")
        config.set("Administration", "")

        config.add_section("Bot")
        config.set("Bot", "gameName", "")
        config.set("Bot", "gameUrl", "https://wwww.twitch.tv/logout")
        config.set("Bot", "gameType", "0")
        config.set("Bot", "")

        config.add_section("Voting")
        config.set("Voting", "voteEnabled", "true")
        config.set("Voting", "voteSkipEnabled", "true")
        config.set("Voting", "voteShuffleEnabled", "true")
        config.set("Voting", "votePercentage", "0.75")
        
        # Someone has altered the settings. Return it back to normal but leave it in config this time
        try:
            if(self.addPlaylistEnabled == False):
                config.set("Voting", "")
                config.add_section("Youtube")
                config.set("Youtube", "addPlaylist", "true")
        except AttributeError:
            pass
        
        with open(self.file, "w", encoding="utf-8") as file:
            config.write(file)

    def update(self):
        config = configparser.ConfigParser(allow_no_value=True)

        # Update info from the class values in config in case we changed during the usage or if things were missing from boot
        config.add_section("Auth")
        config.set("Auth", "useToken", "true") if (self.useToken == True) else config.set("Auth", "useToken", "false")
        config.set("Auth", "token", self.token) if self.token else config.set("Auth", "token", "")
        config.set("Auth", "email", self.email) if self.email else config.set("Auth", "email", "")
        config.set("Auth", "password", self.password) if self.password else config.set("Auth", "password", "")
        config.set("Auth", "")

        config.add_section("Administration")
        config.set("Administration", "; Split admins/mods using \",\", don't use spaces. To grant access use the id of the user you wish to add.")
        config.set("Administration", "Administrator", ",".join(self.admin)) if self.admin else config.set("Administration", "Administrator", "")
        config.set("Administration", "Moderator", ",".join(self.mod)) if self.mod else config.set("Administration", "Moderator", "")
        config.set("Administration", "; Split textChannel also using \",\", don't use spaces.")
        config.set("Administration", "googleAPI", self.googleAPI) if self.googleAPI else config.set("Administration", "googleAPI", "")
        config.set("Administration", "textChannel", ",".join(self.textChannel)) if self.textChannel else config.set("Administration", "textChannel", "")
        config.set("Administration", "voiceChannel", self.voiceChannel) if self.voiceChannel else config.set("Administration", "voiceChannel", "")
        if self.logChannel:
            config.set("Administration", "logChannel", self.logChannel)
        config.set("Administration", "usePrefix", "true") if (self.usePrefix == True) else config.set("Administration", "usePrefix", "false")
        config.set("Administration", "prefix", self.prefix) if self.prefix else config.set("Administration", "prefix", "")
        config.set("Administration", "")

        config.add_section("Bot")
        config.set("Bot", "gameName", self.gameName) if self.gameName else config.set("Bot", "gameName", "")
        config.set("Bot", "gameUrl", self.gameUrl) if self.gameUrl else config.set("Bot", "gameUrl", "https://wwww.twitch.tv/logout")
        config.set("Bot", "gameType", str(self.gameType)) if self.gameType else config.set("Bot", "gameType", "0")
        config.set("Bot", "")

        config.add_section("Voting")
        config.set("Voting", "voteEnabled", self.voteEnabled) if (self.voteEnabled == False) else config.set("Voting", "voteEnabled", "true")
        config.set("Voting", "voteSkipEnabled", self.voteSkipEnabled) if (self.voteSkipEnabled == False) else config.set("Voting", "voteSkipEnabled", "true")
        config.set("Voting", "voteShuffleEnabled", self.voteShuffleEnabled) if (self.voteShuffleEnabled == False) else config.set("Voting", "voteShuffleEnabled", "true")
        config.set("Voting", "votePercentage", str(self.votePercentage)) if isinstance(self.votePercentage, float) else config.set("Voting", "votePercentage", "0.75")
        config.set("Voting", "")
        
        if(self.addPlaylistEnabled == False):
            config.add_section("Youtube")
            config.set("Youtube", "addPlaylistEnabled", self.addPlaylistEnabled)
            
        with open(self.file, "w", encoding="utf-8") as file:
            config.write(file)

bot = MusicBot()
bot.run()