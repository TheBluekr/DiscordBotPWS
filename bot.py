version = "0.1a"

import discord
import logging
import os
import configparser

# Define root logger

class Discord(discord.Client):
  # Init discord.Client() from discord.py
  def __init__(self):
    super().__init__()
    # Add more code for init (declare vars)
    # Get info from configparser
    # Define class logger
    
    self.channel = None
    self.voiceChannel = None
    self.logChannel = None
    self.musicPlaylist = list()

  async def on_ready(self):
    # Initialize login and states
    self.logger.info("Succesfully logged in as {name}".format(name=self.user.name))
    

  async def on_message(self, message):
    # Parse message for commands

  async def on_voice_state_update(self, memberBefore, memberAfter):
    # Process voicestate updates from clients connected to voicechannel

  def run(self):
    self.logger.info("Logging in")
    # No comment needed
    if(self.useToken):
      super().login(self.userToken)
    else:
      super().login(self.userName,self.userPassword)

class Config:
  def __init__(self, file):
    self.file = file
    
    # Add check for existence of file, if not, make one
    
    # Read the config for vars
    config = configparser.ConfigParser()
    config.read(self.file, encoding="utf-8")
    
    # Parse all vars
    self.useToken = config.getboolean("Auth", "useToken", fallback=True)

    if not self.useToken:
      self.logger.info("Token usage is set to false")
      self.logger.info("Loading e-mail and password")
      
      self.email = config.get("Auth", "email", fallback=None)
      self.password = config.get("Auth", "password", fallback=None)
      
      if not (self.email && self.password):
        if not self.email:
          self.logger.critical("E-mail isn't configurated in the config!")
        if not self.password:
          self.logger.critical("Password isn't configurated in the config!")
        self.logger.critical("Logging in won't work, requirements aren't met!")
    else:
      self.logger.info("Token usage is set to true")
      self.logger.info("Loading token")
      
      self.token = config.get("Auth", "token", fallback=None)
      
      if not self.token:
        self.logger.critical("Bot token isn't configurated in the config!")
        self.logger.critical("Logging in won't work, requirements aren't met!")

    # Define channels we can use as bot
    self.textChannel = config.get("Administration", "textChannel", fallback=None)
    self.textChannel = self.textChannel.split(",")
    
    self.voiceChannel = config.get("Administration", "voiceChannel", fallback=None)
    self.voiceChannel = self.voiceChannel.split(",")
    if(len(self.voiceChannel)>1):
      # If someone improperly configurated voicechannel, take first as default
      self.voiceChannel = self.voiceChannel[0]

    # Load Google API
    self.logger.info("Loading Google API token")
    self.googleAPI = config.get("Administration", "googleAPI", fallback=None)
    if not self.googleAPI:
      self.logger.warning("Google API key isn't configured, some features will not work as intended")

    # Load a game which the bot seems to play
    self.gameName = config.get("Bot", "gameName", fallback=None)
    self.gameUrl = config.get("Bot", "gameUrl", fallback=None)
    self.gameType = config.get("Bot", "gameType", fallback=None)
    if self.gameName:
      if(self.gameUrl && (self.gameType == 1)):
        self.logger.info("Loaded stream {name}".format(name=self.gameName))
      else:
        self.logger.info("Loaded game {name}".format(name=self.gameName))

bot = Discord()
bot.run()
