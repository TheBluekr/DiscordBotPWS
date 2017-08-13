version = "0.0.1b"

# ToDo:
# Fix change_presence at on_ready (done?)
# Begin setting up on_message event
# Add exceptionMessage() to get custom error messages for both console and discord (later)
# Add basic commands
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
            self.playlist = json.load(self.fPlaylist, "r")
        except:
            # Either file has a mistake in indentations, has been corrupted or didn't exist. Let's create a new one later
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
        self.playerVolume = 1.0

        # Server related setup
        self.textChannelId = self.config.textChannel
        self.textChannel = None
        self.voiceChannelId = self.config.voiceChannel
        self.voiceChannel = None
        self.voiceClient = None
        self.logChannelId = None
        self.logChannel = None
        self.server = None
        
        self.admin = self.config.admin
        self.mod = self.config.mod

        self.game = discord.Game()
        self.game.name = self.config.gameName
        self.game.url = self.config.gameUrl
        self.game.type = self.config.gameType
        
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
            self.logger.info("Set vote requirement percentage to \"{percentage\"".format(percentage=self.votePercentage))
        else:
            self.logger.info("Voting disabled")
            self.voteSkipEnabled = False
            self.voteShuffleEnabled = False
            
        self.googleAPI = self.config.googleAPI
        
        self.youtube = Youtube(self.googleAPI)

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

#        if self.config.googleAPI:
#            for song in self.playListUrl:
#                # Let's retrieve all info we got, we'll receive None for title or duration if something went wrong
#                video = self.youtube.getVideo(song)
#                if(video.title and video.duration):
#                    self.playList.append([video.url, video.title, video.duration])
#                elif(video.url):
#                    self.playList.append([video.url])
#                else:
#                    self.logger.warning("Couldn't retrieve any info about \"{url}\", is this video private or removed?")
#        else:
#            for song in self.playListUrl:
#                self.playList.append([song])
#        self.logger.info("Loaded {amount} songs".format(amount=len(self.playList)) if len(self.playList) != 1 else self.logger.info("Loaded {amount} song".format(amount=len(self.playList))
        
        # We'll receive None if not found
        self.textChannel = self.get_channel(self.textChannelId)
        self.voiceChannel = self.get_channel(self.voiceChannelId)
        self.logChannel = self.get_channel(self.logChannelId)
        if self.textChannel:
           self.server = self.textChannel.server

    async def on_message(self, message):
        # First check if it's us being tagged or correct prefix is being used
        if(self.flagUsePrefix == False):
            # Prevent issues, if this is smaller than 0 (wat?), we got a problem
            if(len(message.raw_mentions) == 0):
                return
            # It wasn't us who got tagged first, just ignore it I guess
            if(message.raw_mentions[0] != self.user.id):
                return
        elif((self.flagUsePrefix == True) and (self.prefix != None)):
            if(not message.content.startswith(self.prefix)):
                return
        else:
            # If neither of these match, propably something went wrong in the config
            self.logger.error("The prefix isn't configured correctly! Updating config to default mention")
            self.config.usePrefix = False
            self.flagUsePrefix = False
            self.config.update()
            try:
                await self.send_message(message.channel, "Something went wrong, please try again using \n{prefix} {content}```".format(prefix=self.user.mention, content = message.content.split(' ', 1)[1]))
            except IndexError:
                await self.send_message(message.channel, "Something went wrong, please try again") 
            return

        # Remove first prefix or mention we checked
        try:
            # Credits to Plue for informing me about this method
            content = message.content.split(' ', 1)[1]
        except IndexError:
            return
            # In case we only mention the bot or use a prefix it can create exceptions

        # We want to make sure there's something after the add, it can't be empty right?
        if content.startswith("add"):
            if content.strip() == "add":
                self.logger.error("No arguments were passed after \"add\", aborting")
                await self.send_message(message.channel, formatErrorSyntax.format(format="```\"{prefix} add <URL / id>\"```".format(prefix=self.formatPrefix)))
                return

            content = content.replace("add ", "", 1)
            # We got something prioritized, lets add some checks
            if (len(content.split(' ', 1)) == 2):
                if ((message.author in self.mods) or (message.author in self.admins)):
                    try:
                        queuePos = int(content.split(' ', 1)[1])
                        if queuePos == 0:
                            queuePos += 1
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
            
            songList = list()
            song = list()
            
            # Add support for complete playlists if we have the API
            # It could happen we had an shortened one so we can't take full link
            if(content.startswith("https://www.youtu") or content.startswith("www.youtu")):
                self.logger.debug("Received link: \"{link}\", parsing".format(link=content))
                # We declared youtube class at __init__, let's call it again with a key registered
                url = self.youtube.parse(content)
                if(url["typeUrl"] == "video"):
                    self.logger.debug("Received video with id \"{id}\"".format(id=url["url"]))
                elif(url["typeUrl"] == "list"):
                    self.logger.debug("Received list with id \"{id}\"".format(id=url["url"]))
                # Add youtube API requests here
                # <code>
                if (url["typeUrl"] == "video"):
                    #if (self.googleAPI):
                    if (False):
                        pass
                        # Add code for retrieving info from Youtube
                    else:
                        song.append(url["url"])
                        song.append(message.author.id)
                        songList.append(song)
                elif(url["typeUrl"] == "list"):
                    await self.send_message(message.channel, "Lists adding isn't supported... for now")
                else:
                    # We'll receive an unknown typeUrl when googleAPI isn't configured
                    pass
                
            # Easy method to parse multiple songs in case, not efficient for 1 only
            for song in songList:
                self.playlist.insert(queuePos+songList.index(song), song)
            if(len(songList) == 1):
                if(len(song) == 2):
                    await self.send_message(message.channel, "Added {url} at position {pos}".format(url=song[0], pos=queuePos))
                else:
                    await self.send_message(message.channel, "Added {song} at position {pos}".format(song=None, pos=queuePos))

        if content.startswith("play"):
            if len(self.playlist) == 0:
                await self.send_message(message.channel, "Playlist is empty")
                return
            if self.is_voice_connected(self.server):
                if(self.user.voice.voice_channel != self.voiceChannel):
                    return
                while len(self.playlist > 0):
                    # We've got 3 elements in the list when the API was used and an author which added it
                    if(len(self.playlist[0]) == 4):
                        self.logger.debug("Preparing {song} (\"{id}\", \"{duration}\"), added by {author} (\"{authorId}\")".format(song=self.playlist[0][1], id=self.playlist[0][0], duration=self.playlist[0][2], author=self.get_member(self.playlist[0][3]), authorId=self.playlist[0][3]))
                    else:
                        self.logger.debug("Preparing song (\"{id}\"), added by {author} (\"{authorId}\")".format(id=self.playlist[0][0], author=self.get_member(self.playlist[0][3]), authorId=self.playlist[0][3]))
                    self.voteSkip = False
                    self.voteShuffle = False
                    self.player = await self.voiceClient.create_ytdl_player(self.playlist[0][0])
                    # Based on API we should receive None when youtube-dl fails to extract info
                    if self.player.title == None:
                        self.logger.error("Youtube-dl failed to extract info from \"{title}\"".format(title=self.playlist[0][0]))
                        del self.playlist[0]
                        continue
                    self.player.volume = self.playerVolume
                    self.player.start()
                    if (len(self.playlist[0] == 4):
                        await self.send_message(message.channel, "Started playing {song}".format(song=self.player.title))
                    else:
                        await self.send_message(message.channel, "Started playing {song}".format(song=self.playlist[0][1]))
                    while(self.player.is_playing() and not self.player.is_done()):
                        await asyncio.sleep(1)
                        if(self.voteShuffle):
                            if len(self.playlist) > 2):
                                # We want to make sure we're not going to repeat our current song
                                self.song = self.playlist[0]
                                del self.playlist[0]
                                random.shuffle(self.playlist)
                                self.playlist.insert(0, self.song)
                                self.voteShuffleList = list()
                                self.voteShuffle = False
                                await self.send_message(message.channel, "Shuffling playlist")
                            else:
                                self.voteShuffleList = list()
                                self.voteShuffle = False
                                await self.send_message(message.channel, "Playlist is too short to shuffle!")
                        if(self.voteSkip):
                            self.voteSkipList = list()
                            self.voteSkip = False
                            await self.send_message(message.channel, "Skipping current song")
                            break
                    # Prevent further things from happening at other commands
                    self.player = None
                    self.voteSkipList = list()
                    self.voteSkip = False
                    del self.playlist[0]

        if content.startswith("eval"):
            if content.strip() == "eval":
                self.logger.error("No arguments were passed after \"eval\", aborting")
                await self.send_message(message.channel, formatErrorSyntax.format(format="```\"{prefix} eval <value>\"```".format(prefix=self.formatPrefix)))
                return

            content = content.replace("eval ", "", 1)
            # Censor private info from anyone
            if ("self.email" or "self.password" or "self.token" or "self.config.email" or "self.config.password" or "self.config.token") in content:
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
        # Process voicestate updates from clients connected to voicechannel
        updateVoteState = False
        super().checkVoiceClient()
        if((memberBefore.voice.voice_channel != self.voiceChannel) or (memberAfter.voice.voice_channel) != self.voiceChannel))
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
                super().updateVoteState()
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
                super().updateVoteState()
            return

    def updateVoteState(self):
        if self.is_voice_connected(self.server):
            if(self.user.voice.voice_channel == self.voiceChannel):
                voiceMembers = list()
                # Check if 75% of the voice members matching the criteria has voted
                for member in self.voiceChannel.voice_members:
                    if member == self.user:
                        continue
                    if (member.voice.deaf or member.voice.self_deaf):
                        continue
                    voiceMembers.append(member)
                if((len(voiceMembers)/len(self.voteSkipList) >= self.votePercentage) and voteSkipEnabled):
                    self.voteSkip = True
                if((len(voicemembers)/len(self.voteShuffleList) >= self.votePercentage) and voteShuffleEnabled):
                    self.voteShuffle = True
    
    def checkVoiceClient(self):
        if self.is_voice_connected(self.server):
            if self.user.voice.voice_channel == self.voiceChannel:
                if(len(self.voiceChannel.voice_members) == 1):
                    self.voiceClient = self.voice_client_in(self.server)
                    await self.voiceClient.disconnect()
                    self.voiceClient = None
                else:
                    # Nothing to be concerned about, resume earlier code
                    return
            else:
                # Guess we got moved, lets go back
                await self.move_to(self.voiceChannel)
                self.voiceClient = self.voice_client_in(self.server)
        else:
            self.voiceClient = await self.join_voice_channel(self.voiceChannel)

    async def on_server_join(self, server):
        pass

    def run(self):
        self.logger.info("Logging in")
        # No comment needed to explain this
        if(self.flagUseToken):
            if(self.userToken == None):
                self.logger.critical("Token isn't defined, aborting")
                return
            await super().start(self.userToken)
        else:
            if((self.userName == None) or (self.userPassword == None)):
                self.logger.critical("Login credentials aren't defined, aborting")
                return
            await super().start(self.userName,self.userPassword)

class Youtube:
    def __init__(self, key=None):
        self.key = key
        
    def getList(self, list):
        pass
    
    def getVideo(self, video):
        pass

    def parse(self, url):
        # Use this if we get a https://www.youtube.com/ link
        url_data = urllib.parse.urlparse(url)
        data = urllib.parse.parse_qs(url_data.query)
        if "list" in data:
            return {"url":data["list"][0],"typeUrl":"list"}
        elif "v" in data:
            return {"url":data["v"][0],"typeUrl":"video"}

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
            self.admin = None
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
            self.mod = None
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
            self.textChannel = None
        if self.textChannel:
            self.textChannel = self.textChannel.split(",")

        self.voiceChannel = config.get("Administration", "voiceChannel", fallback=None)
        if self.voiceChannel == "":
            self.voiceChannel = None
        if self.voiceChannel:
            self.voiceChannel = self.voiceChannel.split(",")
            if(len(self.voiceChannel > 1) and (isinstance(self.voiceChannel, list) == True)):
                self.voiceChannel = self.voiceChannel[0]
        
        self.logChannel = config.get("Administration", "logChannel", fallback=None)
        if self.logChannel == "":
            self.logChannel = None
        if self.logChannel:
            self.logChannel = self.logChannel.split(",")
            if(len(self.logChannel > 1) and (isinstance(self.voiceChannel, list) == True)):
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

        self.voteEnabled = config.getboolean("Voting", "voteEnabled")
        self.voteSkipEnabled = config.getboolean("Voting", "voteSkipEnabled")
        self.voteShuffleEnabled = config.getboolean("Voting", "voteShuffleEnabled")
        self.votePercentage = config.getfloat("Voting", "votePercentage")

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
        config.set("Administration", "usePrefix", "false")
        config.set("Administration", "prefix", "")
        config.set("Administration", "")

        config.add_section("Bot")
        config.set("Bot", "gameName", "")
        config.set("Bot", "gameUrl", "https://wwww.twitch.tv/logout")
        config.set("Bot", "gameType", "0")

        config.set("Voting", "voteEnabled", "true")
        config.set("Voting", "voteSkipEnabled", "true")
        config.set("Voting", "voteShuffleEnabled", "true")
        config.set("Voting", "votePercentage", "0.75")

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
        config.set("Administration", "; Split admins/mods using \",\" don't use spaces. To grant access use the id of the user you wish to add.")
        config.set("Administration", "Administrator", self.admin) if self.admin else config.set("Administration", "Administrator", "")
        config.set("Administration", "Moderator", self.mod) if self.mod else config.set("Administration", "Moderator", "")
        config.set("Administration", "")
        config.set("Administration", "googleAPI", self.googleAPI) if self.googleAPI else config.set("Administration", "googleAPI", "")
        config.set("Administration", "textChannel", self.textChannel) if self.textChannel else config.set("Administration", "textChannel", "")
        config.set("Administration", "voiceChannel", self.voiceChannel) if self.voiceChannel else config.set("Administration", "voiceChannel", "")
        config.set("Administration", "usePrefix", "true") if (self.usePrefix == True) else config.set("Administration", "usePrefix", "false")
        config.set("Administration", "prefix", self.prefix) if self.prefix else config.set("Administration", "prefix", "")
        config.set("Administration", "")

        config.add_section("Bot")
        config.set("Bot", "gameName", self.gameName) if self.gameName else config.set("Bot", "gameName", "")
        config.set("Bot", "gameUrl", self.gameUrl) if self.gameUrl else config.set("Bot", "gameUrl", "https://wwww.twitch.tv/logout")
        config.set("Bot", "gameType", str(self.gameType)) if self.gameType else config.set("Bot", "gameType", "0")
        config.set("Bot", "")

        config.set("Voting", "voteEnabled", self.voteEnabled) if (self.voteEnabled == False) else config.set("Playlist", "voteEnabled", "true")
        config.set("Voting", "voteSkipEnabled", self.voteSkipEnabled) if (self.voteSkipEnabled == False) else config.set("Playlist", "voteSkipEnabled", "true")
        config.set("Voting", "voteShuffleEnabled", self.voteShuffleEnabled) if (self.voteShuffleEnabled == False) else config.set("Playlist", "voteShuffleEnabled", "true")
        config.set("Voting", "votePercentage", str(self.votePercentage)) if isinstance(self.votePercentage, float) else config.set("Playlist", "votePercentage", "0.75")

class Embed:
    def __init__(self, author=None, title=None, url=None, **kwargs):
        pass

    def embed(self):
        embed = discord.Embed()
        return None # For now

bot = MusicBot()
bot.run()
