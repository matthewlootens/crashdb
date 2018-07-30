import configparser

class Config:
    def __init__(self, filename):
        with open(filename) as f:
            self.config = configparser.ConfigParser()
            self.config.read_file(f)

    def get_config_settings(self):
        return self.config
