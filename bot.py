version = "0.0.1b"

# ToDo:
# Fix change_presence at on_ready (done?)
# Begin setting up on_message event
#     Add exceptionMessage() to get custom error messages for both console and discord
# Add basic commands
# Define setup event when joining server
# Take current create_ytdl_player function from discord.py and use it on local level
# Prepare for future rewrite

import discord
import logging
import os
import configparser
import datetime
import urllib.parse
import traceback

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
            self.logger.warning("Settings folder was missing, created it")

        self.fConfig = os.path.join("./settings", "config.cfg")

        self.version = version

        self.config = Config(self.fConfig)

        # Get auth
        if self.config.useToken:
            self.flagUseToken = True
            self.userToken = self.config.token
        else:
            self.flagUseToken = False
            self.userName = self.config.email
            self.userPassword = self.config.password

        if not self.config.usePrefix:
            self.logger.info("usePrefix set as false in config, using defaults")
            self.prefix = None
            self.flagUsePrefix = False
        else:
            self.logger.info("usePrefix set as true in config, loaded {name} as prefix".format(name=self.config.prefix))
            self.prefix = self.config.prefix
            self.flagUsePrefix = True

        # Server related setup
        self.textChannelId = self.config.textChannel
        self.textChannel = None
        self.voiceChannelId = self.config.voiceChannel
        self.voiceChannel = None
        self.logChannelId = None
        self.logChannel = None
        self.serverId = None
        self.musicPlaylist = list()

        self.game = discord.Game()
        self.game.name = self.config.gameName
        self.game.url = self.config.gameUrl
        self.game.type = self.config.gameType
        
        self.youtube = Youtube(self.config.googleAPI)

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

    async def on_message(self, message):
        # First check if it's us being tagged or correct prefix is being used
        if(self.flagUsePrefix == False):
            # Prevent issues, if this is smaller than 0 (wat?), Houston, we got a problem
            if(len(message.raw_mentions) == 0):
                return
            if(message.raw_mentions[0] != self.user.id):
                return
        elif((self.flagUsePrefix == True) and (self.prefix != None)):
            if(not message.content.startswith(self.prefix)):
                return
        else:
            # If neither of these match, we propably did something wrong in the config
            self.logger.critical("The prefix isn't configured correctly! Aborting")
            return

        # Remove first prefix or mention we checked
        try:
            content = message.content.split(' ', 1)[1]
        except IndexError:
            return
            # In case we only mention the bot or use a prefix it can create exceptions

        # We want to make sure there's something after the add, it can't be empty right?
        if content.startswith("add"):
            if content == "add":
                format = exceptionMessage("add")
                await self.send_message(message.channel, format)
                return

            content = content.replace("add ", "", 1)
            self.logger.info("Received link: \"{link}\", parsing".format(link=content))

        if content.startswith("eval"):
            if content == "eval":
                format = exceptionMessage("eval")
                await self.send_message(message.channel, format)
                return

            content = content.replace("eval ", "", 1)
            try:
                output = eval(content)
                await self.send_message(message.channel, "```{output}```".format(output=output))
            except:
                await self.send_message(message.channel, "```{error}```".format(error=traceback.format_exc()))

        if(content.startswith("exit") or content.startswith("shutdown")):
            await self.logout()

    async def on_voice_state_update(self, memberBefore, memberAfter):
        # Process voicestate updates from clients connected to voicechannel
        pass

    async def on_server_join(self, server):
        pass

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
        else:
            return {"url":data["v"][0],"typeUrl":"v"}

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
        if self.useToken == "":
            # Add fallback to True if it's undefined
            self.useToken = True

        if not self.useToken:
            self.logger.info("Token usage is set to false")
            self.logger.info("Loading e-mail and password")

            self.email = config.get("Auth", "email", fallback=None)
            # Fallback to None if it's empty, configparser doesn't support None
            if self.email == "":
                self.email = None
            self.password = config.get("Auth", "password", fallback=None)
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

            self.token = config.get("Auth", "token", fallback=None)
            if self.token == "":
                self.token = None
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
            self.logger.warning("An monderator isn't configured, access is available to admin only")

        # Load Google API
        self.logger.info("Loading Google API token")
        self.googleAPI = config.get("Administration", "googleAPI", fallback=None)
        if self.googleAPI == "":
            self.googleAPI = None
        if not self.googleAPI:
           self.logger.warning("Google API key isn't configured, some features will not work as intended")

        # Define channels we can use as bot
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
            # If someone improperly configurated voicechannel, take first as default
            if(len(self.voiceChannel > 1) and (isinstance(self.voiceChannel, list) == True)):
                self.voiceChannel = self.voiceChannel[0]

       # Use by default not a custom prefix, if true, use the configured one
        self.usePrefix = config.get("Administration", "usePrefix", fallback=False)
        if self.usePrefix == "":
            self.usePrefix = None
        if not self.usePrefix:
            self.logger.info("Prefix usage is set to false")
            self.logger.info("Configuring bot mention as prefix on login")
        else:
            self.logger.info("Prefix usage is set to true")
            self.logger.info("Loading prefix")
            self.prefix = config.get("Administration", "prefix", fallback=None)
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

    def reset(self):
        config = configparser.ConfigParser()

        self.logger.warning("Resetting the config to default values")
        # Set auth section up with no values (done)
        config.add_section("Auth")
        config.set("Auth", "useToken", "true")
        config.set("Auth", "email", "")
        config.set("Auth", "password", "")
        config.set("Auth", "token", "")

        config.add_section("Administration")
        config.set("Administration", "Administrator", "")
        config.set("Administration", "Moderator", "")
        config.set("Administration", "", "")
        config.set("Administration", "googleAPI", "")
        config.set("Administration", "textChannel", "")
        config.set("Administration", "voiceChannel", "")
        config.set("Administration", "usePrefix", "false")
        config.set("Administration", "prefix", "")

        config.add_section("Bot")
        config.set("Bot", "gameName", "")
        config.set("Bot", "gameUrl", "")
        config.set("Bot", "gameType", "0")

        with open(self.file, "w", encoding="utf-8") as file:
            config.write(file)

    def update(self):
        config = configparser.ConfigParser()

        self.logger.info("Updating info in config")
        # Update info from the class values in config in case we changed during the usage
        config.add_section("Auth")
        config.set("Auth", "useToken", self.useToken)
        config.set("Auth", "email", self.email)
        config.set("Auth", "password", self.password)
        config.set("Auth", "token", self.token)

        config.add_section("Administration")
        config.set("Administration", "Administrator", self.admin)
        config.set("Administration", "Moderator", self.mod)
        config.set("Administration", "", "")
        config.set("Administration", "googleAPI", self.googleAPI)
        config.set("Administration", "textChannel", self.textChannel)
        config.set("Administration", "voiceChannel", self.voiceChannel)
        config.set("Administration", "usePrefix", self.usePrefix)
        config.set("Administration", "prefix", self.prefix)

        config.add_section("Bot")
        config.set("Bot", "gameName", self.gameName)
        config.set("Bot", "gameUrl", self.gameUrl)
        config.set("Bot", "gameType", self.gameType)

class Embed:
    def __init__(self):
        pass

    def embed(self, author=None, title=None, url=None, **kwargs):
        pass

bot = MusicBot()
bot.run()
