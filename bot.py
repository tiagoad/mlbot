import datetime
import logging
import os
import pickle
import time
import pytz
from urllib.request import urlopen
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from enum import Enum

import twitter
from twitter.error import TwitterError

class Line:
    def __init__(self, name, emoji):
        self.name = name
        self.emoji = emoji

class MLStatus:
    def __init__(self, message, ok):
        self.message = message
        self.ok = ok

class MLBot:
    TIMEZONE = 'Europe/Lisbon'
    STATUS_URL = 'http://app.metrolisboa.pt/status/estado_Linhas.php'
    LINES = [
        Line('Amarela', '\U0001F34B'),
        Line('Vermelha', '\U000FE051'),
        Line('Azul', '\U0001F433'),
        Line('Verde', '\U0001F34F')
    ]

    STRINGS = {
        "LINE": "Linha",
        "UP_EMOJI": "\U0001F535",
        "DOWN_EMOJI": "\U0001F534"
    }

    def __init__(self, state_file, twitter_config, telegram_config, pretend=False):
        """
        Initializes a bot instance

        :param state_file: File where state will be stored
        :param twitter_config: Twitter configuration
        :param telegram_config: Telegram configuration
        """
        self.state_file = state_file
        self.pretend = pretend

        if not self.pretend:
            self.twitter = twitter.Api(**twitter_config)
            self.twitter.VerifyCredentials()
        
        self.telegram_config = telegram_config

        self.tz = pytz.timezone(self.TIMEZONE)

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
                self.state_change(line, current)

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

        for line in self.LINES:
            el = soup.select('td.linha_%s li' % line.name.lower())[0]

            message = el.text
            ok = 'semperturbacao' in el.parent.get('class', [])

            status[line.name] = MLStatus(
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

        self.publish("%s %s %s: %s" % (
            emoji,
            self.STRINGS["LINE"],
            line,
            message))
            
    def publish(self, message):
        self.log.info('Publishing: %s', message)
                
        self.publish_twitter(message)
        self.publish_telegram(message)

    def publish_telegram(self, message):
        """
        Publishes a message to telegram.
        
        :param message: Message to publish
        """
        
        key = self.telegram_config['api_key']
        
        for dst in self.telegram_config['destination']:
            data = urlencode(dict(
                chat_id=dst,
                parse_mode='HTML',
                text=message
            )).encode('utf-8')
                    
            res = urlopen(f'https://api.telegram.org/bot{key}/sendMessage', data=data)

    def publish_twitter(self, message):
        """
        Publishes a message to twitter.

        :param message: Message to publish
        """

        # add a timestamp to avoid duplicates
        now = datetime.datetime.now()
        now_tz = pytz.utc.localize(now).astimezone(self.tz)
        timestamp = now_tz.strftime("[%H:%M]")

        # split into tweets
        parts = []
        words = message.split(" ")
        while len(words) > 0:
            part = timestamp

            while len(words) > 0:
                joined = part + " " + words[0]
                if len(joined) < 270:
                    part = joined
                    words.pop(0)
                else:
                    break

            parts.append(part)

        for part in parts:
            try:
                if not self.pretend:
                    self.twitter.PostUpdate(part)
                    
            except TwitterError as e:
                error = e.message
                if (len(error) > 0 and
                    error[0].get('code') == 187):

                    # Duplicate? Add a dot.
                    self.publish_twitter(message + '.')
                else:
                    raise e

if __name__ == '__main__':
    # set up logger
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)-9s %(message)s")
        
        
    debug = os.environ.get('BOT_DEBUG', '0') == '1'
    pretend = os.environ.get('BOT_PRETEND', '0') == '1'

    log = logging.getLogger('mlbot')    
    log.setLevel(logging.DEBUG if debug else logging.INFO)

    try:
        state_file = os.environ['BOT_STATE_FILE']

        bot = MLBot(
            state_file, 
            twitter_config=dict(
                consumer_key=os.environ['TWITTER_CONSUMER_KEY'],
                consumer_secret=os.environ['TWITTER_CONSUMER_SECRET'],
                access_token_key=os.environ['TWITTER_ACCESS_TOKEN_KEY'],
                access_token_secret=os.environ['TWITTER_ACCESS_TOKEN_SECRET']
            ) if not pretend else {},
            telegram_config=dict(
                api_key=os.environ['TELEGRAM_KEY'],
                destination=os.environ['TELEGRAM_DESTINATION'].split(',')
            ),
            pretend=pretend)
    except KeyError as e:
        log.critical('Environment variable %s not found.' % e)
        
    bot.check()
