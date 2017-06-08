import configparser

class Configparser()
  def __init__(self):
    # Declare default for now
    self.config = configparser.Configparser()
    self.config.get("./settings/config.cfg") # Fix making a folder with file in case not existing
    self.userName = None
    self.userPassword = None
    self.userToken = None
    self.useToken = False
    self.channel = None
    self.voiceChannel = None
    self.logChannel = None
