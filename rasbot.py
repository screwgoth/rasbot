# -*- coding: utf-8 -*-
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from chatterbot.trainers import ChatterBotCorpusTrainer
import os
import time
from slackclient import SlackClient

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
VSPHERE_USERNAME = os.environ.get("VSPHERE_USERNAME")
VSPHERE_PASSWORD = os.environ.get("VSPHERE_PASSWORD")
#SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")
SLACK_CHANNEL = os.environ.get("MY_SLACK_ID")

# constants
#AT_BOT = "<@" + BOT_ID + ">:"
AT_BOT = "<@" + BOT_ID + ">"
EXAMPLE_COMMAND = "tell me"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# Initialize chatterbot
# Create a new instance of a ChatBot
chatterbot = ChatBot("rasbot",
        #storage_adapter="chatterbot.storage.JsonFileStorageAdapter",
        storage_adapter="chatterbot.storage.MongoDatabaseAdapter",
        logic_adapters=[
            "chatterbot.logic.MathematicalEvaluation",
            "chatterbot.logic.BestMatch",
            "chatterbot.logic.DevOpsTasks"
            ],
        input_adapter="chatterbot.input.VariableInputTypeAdapter",
        output_adapter="chatterbot.output.OutputFormatAdapter",
        output_format='text',
        database="chatterbot-database",
        database_uri="mongodb://localhost:27017/"
)

chatterbot.set_trainer(ChatterBotCorpusTrainer)

# chatterbot.train(
#     "chatterbot.corpus.english"
# )

chatterbot.train(
    "chatterbot.corpus.english.greetings",
    "chatterbot.corpus.english.conversations"
)

def handle_command(command, channel):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    response = chatterbot.get_response(command)
    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        #print "output_list : ", output_list
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
            #if output and 'text' in output and 'message' in output['type']:
                # return text after the @ mention, whitespace removed
                #return output['text'].split(AT_BOT)[1].strip().lower(), \
                return output['text'].split(AT_BOT)[1].strip(), \
                       output['channel']
    return None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    my_channel = SLACK_CHANNEL  #Raseel


    greeting = "Hey there, I'm Raseel's chatbot\nI'm still learning the BotLife, so it would help if you interact with me in clear, short sentences"
    slack_client.api_call("chat.postMessage", channel=my_channel,
                          text=greeting, as_user=True)
    if slack_client.rtm_connect():
        print("StarterBot connected and running!")
        while True:
            command, channel = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                handle_command(command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
