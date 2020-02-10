#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# general
import sys
import datetime
from time import sleep

# file handling
import json
import csv

# HTML parsing
from bs4 import BeautifulSoup

# HTTP requests
import urllib.request

# email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import smtplib


CONFIG_FILE = "./config.json"
DB_FILE     = "./last-query.json"
SLEEP_TIME  = 5
ISO_DATE    = "%Y-%m-%dT%H:%M:%S"


class Link:
    def __init__(self, name, url, pub_date=None):
        self.__name = name
        self.__url  = url
        self.__pub_date = pub_date

    def getData(self):
        return (
            self.__name,
            self.__url,
            self.__pub_date
        )

    def print(self, pre="", post=""):
        out = pre
        if self.__pub_date != None:
            out += "[{}] ".format(self.__pub_date.strftime(ISO_DATE))
        out += "\"{}\" -> {}".format(
            self.__name,
            self.__url
        )
        out += post
        return out

    def setDate(self, dt):
        self.__pub_date = dt
        return dt

    def isEqual(self, name, url):
        return (self.__name == name and self.__url == url)


def makePrettyDate(now=datetime.datetime.now()):
    try:
        diff = (now - dt).days
        if diff == 0:
            return "seit heute"
        return "seit {} {}".format(
            diff,
            "Tag" if diff == 1 else "Tagen"
        )
    except:
        return "[???]"


def getWebsiteContent(url):
    page = urllib.request.urlopen(url)
    return page


def extractPdfLinks(content, parser = "html.parser"):
    soup = BeautifulSoup(content, parser)
    main_content = str(soup.select("div#main")[0])

    soup = BeautifulSoup(main_content, parser)
    links = soup.find_all("a")

    pdfs = []
    for l in links:
        title = l.get_text()
        href = l.get("href")
        if href.endswith(".pdf"):
            pdfs.append(Link(title, href))
    return pdfs


def prepareMailServer(smtp_config):
    server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
    server.login(smtp_config["user"], smtp_config["password"])
    return server


def sendEmail(server, sender, recipient, subject, message):
    msg = MIMEMultipart()
    msg["Subject"]      = subject
    msg["From"]         = sender
    msg["To"]           = recipient
    msg["Date"]         = formatdate(localtime = True)
    msg["Content-Type"] = "text/plain; charset=utf-8"
    mailBody = MIMEText(message, "plain", "UTF-8")
    msg.attach(mailBody)

    result = server.sendmail(sender, recipient, msg.as_string())
    return result


def storeQuery(db_file, query, query_date):
    # Create JSON data structure.
    data = {
        "date": query_date.strftime(ISO_DATE),
        "links": []
    }
    for l in query:
        name, url, pub_date = l.getData()
        if pub_date == None:
            pub_date = query_date
        data["links"].append({
            "name":     name,
            "url":      url,
            "pub_date": pub_date.strftime(ISO_DATE)
        })
    # Write JSON DB file.
    data_str = json.dumps(data, indent=2)
    with open(db_file, "w") as f:
        length = f.write(data_str)
    return length


def loadQuery(db_file):
    query = []
    try:
        f = open(db_file, "r")
    except: # no query file yet
        return (query, None)

    data = json.load(f)
    query_date = datetime.datetime.strptime(data["date"], ISO_DATE)
    for l in data["links"]:
        try:
            query.append(Link(
                l["name"],
                l["url"],
                datetime.datetime.strptime(l["pub_date"], ISO_DATE)
            ))
        except:
            print("Warning: Date \"{}\" could not be parsed!".format(
                l["pub_date"]
            ))
    return (query, query_date)


def main():
    # Check for debugging flag (i.e. don't actually send emails).
    DEBUG = (sys.argv[-1] == "--debug")
    if DEBUG:
        print("+" * 60)
        print("NOTE: Running in DEBUG mode!")
        print("  - Not sending any mails at all.")
        print("+" * 60)
        print()

    # Read config.
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    # Load last query results.
    query_old, query_old_date = loadQuery(DB_FILE)
    print("DB file from {} with last {} query results loaded.".format(
        query_old_date.strftime(ISO_DATE) if query_old_date != None else "(unknown)",
        len(query_old)
    ))
    for l in query_old:
        print(l.print(pre = "  - "))

    # Query URL and extract PDF links.
    content = getWebsiteContent(config["url"])
    query = extractPdfLinks(content)
    count_total = len(query)
    print("URL query of \"{}\" finished with {} entries.".format(
        config["url"],
        count_total
    ))
    for l in query:
        print(l.print(pre = "  - "))


    # Get date info from last query and check if there are new links.
    count_new = 0
    for l in query:
        found = False
        name, url, _ = l.getData()
        for l_old in query_old:
            name_old, url_old, pub_date_old = l_old.getData()
            if l.isEqual(name_old, url_old):
                l.setDate(pub_date_old)
                found = True
                break
        if not found:
            count_new += 1

    print("There are {} new PDF links of {} total.".format(
        count_new,
        count_total
    ))

    if count_new > 0:
        # Make subject and message text.
        mail_subject = "Kevelaer: {} {}".format(
            count_new,
            "neuer Gottesdienstplan" if count_new == 1 else "neue Gottesdienstpläne"
        )

        mail_text = "Hallo {name},\n\n"
        mail_text += "es wurden kürzlich neue Gottesdienstpläne für St. Marien Kevelaer veröffentlicht.\n\n"
        for l in query:
            name, url, pub_date = l.getData()
            mail_text += "[{}] {}\n{}\n\n".format(
                (makePrettyDate(pub_date) if pub_date != None else "NEU"),
                name,
                url
            )
        mail_text += "Direkt zur Homepage: {}\n".format(config["url"])
        if query_old_date != None:
            mail_text += "Letzte Überprüfung: {}\n".format(
                query_old_date.strftime("%d.%m.%Y %H:%M:%S")
            )

        mail_text += "Viele Grüße\ndein Raspberry Pi\n"

        print("Generated mail subject: {}".format(mail_subject))
        print("Generated mail text:\n{}".format(mail_text))

        # Login to the SMTP server.
        server = prepareMailServer(config["email"]["sender"])

        # Send a mail to all interested people.
        for rec in config["email"]["recipients"]:
            rec_name, rec_mail = rec
            if not DEBUG:
                sendEmail(
                    server,
                    config["email"]["sender"]["user"],
                    rec_mail,
                    mail_subject,
                    mail_text.format(name = rec_name)
                )
            print("Sent mail to {} ({}).".format(
                rec_name,
                rec_mail
            ))

            # Calm down and insert a short delay.
            sleep(SLEEP_TIME)
    else:
        print("--> Nothing to do here.")

    # Save the current query for the next time.
    bytes_written = storeQuery(DB_FILE, query, datetime.datetime.now())
    print("Query file of {:d} Bytes stored for the next time.".format(bytes_written))


if __name__ == "__main__":
    main()