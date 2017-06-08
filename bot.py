version = "0.1a"

import discord
import logging

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
    super().login(token)

bot = Discord()
bot.run()
