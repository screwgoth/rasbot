import os
import time
import boto.ec2
import atexit
import ssl
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
#from threading import Thread
from slackclient import SlackClient


# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
VSPHERE_USERNAME = os.environ.get("VSPHERE_USERNAME")
VSPHERE_PASSWORD = os.environ.get("VSPHERE_PASSWORD")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")

# constants
#AT_BOT = "<@" + BOT_ID + ">:"
AT_BOT = "<@" + BOT_ID + ">"
EXAMPLE_COMMAND = "tell me"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

def get_vmware_list(esxi_host):
    if hasattr(ssl, '_create_unverified_context'):
          sslContext = ssl._create_unverified_context()
    else:
          sslContext = None

    if hasattr(connect, 'SmartConnectNoSSL'):
        service_instance = connect.SmartConnectNoSSL(host=esxi_host, user=VSPHERE_USERNAME, pwd=VSPHERE_PASSWORD, port=443,sslContext=sslContext)
    else:
        service_instance = connect.SmartConnect(host=esxi_host, user=VSPHERE_USERNAME, pwd=VSPHERE_PASSWORD, port=443, sslContext=sslContext)

    atexit.register(connect.Disconnect, service_instance)
    content = service_instance.RetrieveContent()
    container = content.rootFolder  # starting point to look into
    viewType = [vim.VirtualMachine]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)
    children = containerView.view
    count = 0
    listofVMs = []
    for child in children:
        summary = child.summary
        listofVMs.append(summary.config.name)
        #print listofVMs
    return listofVMs


def get_vmware_count(esxi_host):
    if hasattr(ssl, '_create_unverified_context'):
          sslContext = ssl._create_unverified_context()
    else:
          sslContext = None

    if hasattr(connect, 'SmartConnectNoSSL'):
        service_instance = connect.SmartConnectNoSSL(host=esxi_host, user=VSPHERE_USERNAME, pwd=VSPHERE_PASSWORD, port=443,sslContext=sslContext)
    else:
        service_instance = connect.SmartConnect(host=esxi_host, user=VSPHERE_USERNAME, pwd=VSPHERE_PASSWORD, port=443, sslContext=sslContext)

    atexit.register(connect.Disconnect, service_instance)
    content = service_instance.RetrieveContent()
    container = content.rootFolder  # starting point to look into
    viewType = [vim.VirtualMachine]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)
    children = containerView.view
    count = 0
    for child in children:
        summary = child.summary
        if summary.runtime.powerState == "poweredOn":
            count += 1
    return count

def get_aws_count():
    conn = boto.ec2.connect_to_region("us-east-1", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    reservations = conn.get_all_reservations()
    count = 0
    for reservation in reservations:
        instances = reservation.instances

        for instance in instances:
            if instance.state == 'running':
                count += 1
                tags = instance.tags
                instanceName = 'Default'
                if 'Name' in tags:
                    instanceName = tags['Name']
    return count

def handle_command(command, channel):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    response = "Not sure what you mean. Use the *" + EXAMPLE_COMMAND + \
               "* command to ask me about stuff Eg., @rasbot tell me what should I have for lunch"
    if command.startswith(EXAMPLE_COMMAND):
        if "aws" in command:
            response = "This operation will take some time. Be patient please ..."
            slack_client.api_call("chat.postMessage", channel=channel,
                                  text=response, as_user=True)
            count = get_aws_count()
            response = "There are %d instances running on your AWS" %count
        elif "vmware" in command or "vsphere" in command:
            if "number of" in command or "count" in command:
                if "20.20.4.254" in command:
                    esxi_host = "20.20.4.254"
                elif "10.10.6.254" in command:
                    esxi_host = "10.10.6.254"
                count = get_vmware_count(esxi_host)
                response = "There are %d instances running in Vmware ESXi Host %s" %(count, esxi_host)
            elif "list" in command:
                if "20.20.4.254" in command:
                    esxi_host = "20.20.4.254"
                elif "10.10.6.254" in command:
                    esxi_host = "10.10.6.254"
                listofVms = get_vmware_list(esxi_host)
                vmlist = "\n".join(listofVms)
                response = "List of VMs in VMware ESXi Host %s: \n%s" %(esxi_host, vmlist)
            else:
                response = "Do not understand what you want me to do on Vmware. Can you please re-check that you have provided me the correct info"
        elif "lunch" in command or "dinner" in command:
            response = "How about a Pizza!!"
        elif "time" in command or "weather" in command:
            response = "Don't you have better Gadgets or Apps to tell you about it ?"
        else:
            response = "That's something I'm still learning about !! "
    if "hello" in command or "hi" in command:
        response = "Hello !! Nice to know you have some manners"
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
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel']
    return None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    # my_channel = "D225E316C"
    my_channel = SLACK_CHANNEL  #Raseel
    # my_channel = "U033YUS5E" #Yogesh
    # user_id = "U02SYS3SJ" #Haresh
    # user_id = "U02T1MCL7" #Jay
    # my_channel = "U03P0CRLP" #Milind

    greeting = "Hey there, I'm Raseel's chatbot\nYou can ask me about :\nlunch\nAWS instnces\ntime\nweather\n ... and more by calling me out with @rasbot"
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
