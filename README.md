# MLBOT

Posts the Lisbon Metro status updates to Twitter and Telegram.
Written for use with Docker.

## Running
If an `env` file exists with `KEY=VALUE` mappings for the environment variables:

    docker run --env-file env -d -v /local/directory:/state tiagoad/mlbot

## Environment Variables

* `BOT_DEBUG` - Debug output if set
* `BOT_PRETEND` - Output data to command-line, instead of sending to Twitter
* `RUN_INTERVAL` - Interval between runs, in seconds (defaults to 120 seconds)
* `TWITTER_CONSUMER_KEY` - Twitter consumer key
* `TWITTER_CONSUMER_SECRET` - Twitter consumer secret
* `TWITTER_ACCESS_TOKEN_KEY` - Twitter access token
* `TWITTER_ACCESS_TOKEN_SECRET` - Twitter access token secret
* `TELEGRAM_KEY` - Telegram bot API key
* `TELEGRAM_DESTINATION` - Comma-separated list of telegram channel/group names and IDs

## Directories

* `/state` - Holds variable state
