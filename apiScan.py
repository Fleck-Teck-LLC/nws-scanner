import urllib.request, json, threading, facebook, tweepy, os, smtplib
from email.mime.text import MIMEText
from os.path import exists

#List of Known Alerts to prevent posting the same alert twice. Saved as file so that restarting the script will not send duplicate alerts.
knownAlerts = []
if (exists('alerts.txt')):
    with open('alerts.txt') as infile:
        for line in infile:
            knownAlerts.append(line.strip())

print("National Weather Service Scanner starting...\n")

#Determine if can post to Facebook, twitter, or email. Default is false.
fb = False
tw = False
email = False

#Facebook Configuration
if (('FB_ACCESS_TOKEN' in os.environ) and ('FB_PAGE_ID' in os.environ)):
    fb = True
    graph = facebook.GraphAPI(access_token=os.environ['FB_ACCESS_TOKEN'], version="3.0")
    print("Facebook Token: " + os.environ['FB_ACCESS_TOKEN'])
    print("Facebook Page ID: " + os.environ['FB_PAGE_ID'])
else:
    print("Facebook not provisioned. No alerts will be posted.")

#Twitter Configuration
if (('TW_CONSUMER_KEY' in os.environ) and ('TW_CONSUMER_SECRET' in os.environ) and ('TW_ACCESS_TOKEN' in os.environ) and ('TW_ACCESS_SECRET' in os.environ)):
    tw = True
    twitterAuth = tweepy.OAuthHandler(os.environ['TW_CONSUMER_KEY'], os.environ['TW_CONSUMER_SECRET'])
    twitterAuth.set_access_token(os.environ['TW_ACCESS_TOKEN'], os.environ['TW_ACCESS_SECRET'])
    twitter = tweepy.API(twitterAuth)

    print("Twitter Consumer Key: " + os.environ['TW_CONSUMER_KEY'])
    print("Twitter Consumer Secret: " + os.environ['TW_CONSUMER_SECRET'])
    print("Twitter Access Token: " + os.environ['TW_ACCESS_TOKEN'])
    print("Twitter Access Secret: " + os.environ['TW_ACCESS_SECRET'])
    if ('TW_COUNTIES' not in os.environ):
        print("Twitter counties not set. Each tweet will end with \"for counties:\" with none defined.")
        counties = ""
    else:
        counties = json.loads(os.environ['TW_COUNTIES'])
        print("Twitter Counties: " + os.environ['TW_COUNTIES'])
else: 
    print("Twitter not provisioned. No alerts will be posted.")

#Email Configuration
if (("EM_SERVER" in os.environ) and ("EM_PORT" in os.environ) and ("EM_FROM" in os.environ) and ("EM_TO" in os.environ) and ("EM_SECURE" in os.environ) and ("EM_PASS" in os.environ)):
    email = True
    em_sender = os.environ['EM_FROM']
    em_receivers = os.environ['EM_TO']
    em_server = os.environ['EM_SERVER']
    em_port = os.environ['EM_PORT']
    em_password = os.environ['EM_PASS']

    if ("EM_USERNAME" in os.environ):
        em_username = os.environ["EM_USERNAME"]
    else:
        print("No username provided, login will use " + em_sender + " for authentication")
        em_username = os.environ["EM_FROM"]

    print("Email Sender: " + em_sender)
    print("Email Username: " + em_username)
    print("Email Receivers: " + em_receivers)
    print("Email Server: " + em_server)
    print("Email Port: " + em_port)
    print("Email Password: " + em_password)
else:
    print("Email not provisioned. No alerts will be sent.")

#Fetch JSON from API
def getAlerts():
    threading.Timer(10.0, getAlerts).start()
    with urllib.request.urlopen("https://api.weather.gov/alerts/active?status=actual&message_type=alert&zone="+os.environ['NWS_ZONE_ID']) as url:
        data = json.loads(url.read().decode())

        if  "Invalid" in data["title"] :
            raise Exception('Returned data invalid, please check environment variables.')

        for alert in data["features"]:
            if alert["properties"]["id"] not in knownAlerts:
                #Post to Facebook if Provisioned
                if (fb):
                    graph.put_object(
                        parent_object=os.environ['FB_PAGE_ID'],
                        connection_name="feed",
                        message=alert["properties"]["headline"]+"\n\nAffected region(s): "+alert["properties"]["areaDesc"]+"\n\n"+alert["properties"]["description"]
                    )
                    print("Facebook post requested!")

                #Post to Twitter if Provisioned
                if (tw):
                    #Determine counties for Twitter Only.
                    twitterRegion = " for counties: "
                    for county in counties:
                        if county in alert["properties"]["areaDesc"] :
                            twitterRegion += county + " "

                    twitter.update_status(alert["properties"]["headline"] + twitterRegion)
                    print("Tweet post requested!")

                #Send email alert if Provisioned
                if (email):
                    port = int(em_port)

                    msg = MIMEText("Affected region(s): "+alert["properties"]["areaDesc"]+"\n\n"+alert["properties"]["description"])

                    msg['Subject'] = alert["properties"]["headline"]
                    msg['From'] = em_sender
                    msg['To'] = em_receivers

                    with smtplib.SMTP(em_server, port) as server:
                        server.starttls() # Secure the connection

                        server.login(em_username, em_password)
                        server.sendmail(em_sender, em_receivers, msg.as_string())
                        print("mail successfully sent")

                #Save new alert to KnownAlerts
                knownAlerts.append(alert["properties"]["id"])
                with open('alerts.txt', 'w') as alert_storage:
                    alert_storage.write('\n'.join(str(line) for line in knownAlerts))

                #Log Alerts
                print(alert["properties"]["headline"]+"\n")
                print("Affected region(s): "+alert["properties"]["areaDesc"]+"\n")
                print(alert["properties"]["description"])
                print("\n\n---\n\n")

            #Keep only [NWS Alert Cap] alert ID's saved in memory (knownAlerts), remove the oldest ID's first.
            if len(knownAlerts) > int(os.environ['NWS_ALERT_CAP']) :
                knownAlerts.pop(0)

if (('NWS_ZONE_ID' in os.environ) and ('NWS_ALERT_CAP' in os.environ)):
    print("\nNWS Zone(s): " + os.environ['NWS_ZONE_ID'])
    print("NWS Alert Cap: " + os.environ['NWS_ALERT_CAP'] + "\n\n")
    if ((not fb) and (not tw) and (not email)):
        print("No post / email options set. Logging mode only.")
    getAlerts()
else:
    print("\nError: NWS Zones are not sent. Please refer to documentation to resolve this error.")