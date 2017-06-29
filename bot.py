import logging
import os
import pickle
from urllib.request import urlopen

from bs4 import BeautifulSoup
from enum import Enum

import twitter


class MLStatus:
    def __init__(self, message, ok):
        self.message = message
        self.ok = ok

class MLBot:
    STATUS_URL = 'http://app.metrolisboa.pt/status/estado_Linhas.php'
    LINE_NAMES = ['Amarela', 'Vermelha', 'Azul', 'Verde']
    STRINGS = {
        "LINE": "Linha",
        "APPEND": ""
    }

    def __init__(self, state_file, api_credentials):
        """
        Initializes a bot instance

        :param state_file: File where state will be stored
        :param api_credentials: Twitter API credentials
        """
        self.state_file = state_file

        self.twitter = twitter.Api(**api_credentials)
        self.twitter.VerifyCredentials()

        self.log = logging.getLogger('mlbot')

        self.log.debug('Loading state from file')
        try:
            with open(self.state_file, 'rb') as f:
                self.status = pickle.load(f)
        except FileNotFoundError:
            self.log.warning('File not found, first run?')
            self.status = {}

    def check(self):
        """
        Check the status for changes
        """
        status = self.get_status()

        # check for changes
        for line, current in status.items():
            last = self.status.get(line)

            if last == None:
                pass

            elif ((current.ok != last.ok)
                or (not current.ok and current.message != last.message)):

                self.state_change(line, current)

        # save state
        self.log.debug('Saving state to file')
        self.status = status
        with open(self.state_file, 'wb') as f:
            pickle.dump(self.status, f)


    def get_status(self):
        """
        Downloads and parses status from the Metro website

        :return: MLStatus object
        """
        self.log.debug('Downloading HTML')
        html = urlopen(self.STATUS_URL)

        self.log.debug('Parsing HTML')
        soup = BeautifulSoup(html, 'html.parser')
        status = {}

        for line in self.LINE_NAMES:
            el = soup.select('td.linha_%s li' % line.lower())[0]

            message = el.text
            ok = 'semperturbacao' in el.parent.get('class', [])

            status[line] = MLStatus(
                message=message,
                ok=ok)

        return status

    def state_change(self, line, status):
        """
        A state change ocurred.
        Builds a message and publishes it to Twitter.

        :param line:    Metro line
        :param status:  MLStatus object
        """
        self.log.debug('State for line %s changed: %s', line, status.message)

        emoji = '\u2705' if status.ok else '\u26A0\uFE0F'

        message = status.message[0].upper() + status.message[1:]

        # add full stop if there's none
        if not message.endswith('.'):
            message = message + '.'

        self.publish("%s %s %s: %s %s" % (
            emoji,
            self.STRINGS["LINE"],
            line,
            message,
            self.STRINGS["APPEND"]))

    def publish(self, message):
        """
        Publishes a message to twitter. Trimmed if over 140 characters.

        :param message: Message to publish
        """

        self.log.info('Publishing to Twitter: %s', message)
        self.twitter.PostUpdates(message, continuation='\u2026')

if __name__ == '__main__':
    # set up logger
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)-9s %(message)s")

    log = logging.getLogger('mlbot')
    log.setLevel(logging.DEBUG if 'BOT_DEBUG' in os.environ else logging.INFO)

    try:
        state_file = os.environ['BOT_STATE_FILE']

        api_credentials = {
            'consumer_key': os.environ['TWITTER_CONSUMER_KEY'],
            'consumer_secret': os.environ['TWITTER_CONSUMER_SECRET'],
            'access_token_key': os.environ['TWITTER_ACCESS_TOKEN_KEY'],
            'access_token_secret': os.environ['TWITTER_ACCESS_TOKEN_SECRET'],
        }

        bot = MLBot(state_file, api_credentials)
        bot.check()

    except KeyError as e:
        log.critical('Environment variable %s not found.' % e)
