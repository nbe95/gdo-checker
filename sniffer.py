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
import smtplib


CONFIG_FILE = "./config.json"
DB_FILE     = "./last-query.csv"
SLEEP_TIME  = 5


class Link:
    def __init__(self, name, url, date=None):
        self.__name = name
        self.__url  = url
        self.__date = date

    def getData(self):
        return (
            self.__name,
            self.__url,
            self.__date
        )

    def print(self):
        out = ""
        if self.__date != None:
            out += "[{}] ".format(self.__date.strftime("%Y/%m/%d"))
        out += "\"{}\" -> {}".format(
            self.__name,
            self.__url
        )
        return out

    def setDate(self, date):
        self.__date = date
        return date

    def isEqual(self, name, url):
        return (self.__name == name and self.__url == url)


def dateToString(date):
    return date.strftime("%Y-%m-%d")


def dateFromString(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d")


def makePrettyDate(date):
    diff = (datetime.datetime.today() - date).days
    if date == None:
        return "NEU"
    return "seit {} {}".format(
        diff,
        "Tag" if diff == 1 else "Tagen"
    )


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
    msg["Content-Type"] = "text/plain; charset=utf-8"
    mailBody = MIMEText(message, "plain", "UTF-8")
    msg.attach(mailBody)

    result = server.sendmail(sender, recipient, msg.as_string())
    return result


def storeQuery(db_file, query_db):
    with open(db_file, "w") as f:
        writer = csv.writer(f, delimiter = ",", quotechar = "\"", quoting = csv.QUOTE_MINIMAL)
        for l in query_db:
            name, url, date = l.getData()
            if date == None:
                date = datetime.datetime.today()
            date_str = dateToString(date)
            writer.writerow([name, url, date_str])


def loadQuery(file):
    query = []
    try:
        f = open(file, "r")
    except: # no query file yet
        return query

    reader = csv.reader(f, delimiter = ",", quotechar = "\"")
    for name, url, date_str in reader:
        date = dateFromString(date_str)
        query.append(Link(name, url, date))
    return query


def main():
    # Check for debugging flag (i.e. don't actually send emails).
    DEBUG = (sys.argv[-1] == "--debug")
    if DEBUG:
        print("+++ NOTE: Running in DEBUG mode! +++")
        print("  - Not sending any mails at all.")
        print()

    # Read config.
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    # Load last query results.
    links_old = loadQuery(DB_FILE)
    print("DB file with last query results ({} entries) loaded.".format(len(links_old)))
    for l in links_old:
        print("  -", l.print()),

    # Query URL and extract PDF links.
    content = getWebsiteContent(config["url"])
    links = extractPdfLinks(content)
    count_total = len(links)
    print("URL query of \"{}\" ({} entries) finished.".format(
        config["url"],
        count_total
    ))
    for l in links:
        print("  -", l.print())

    # Get date info from last query and check if there are new links.
    count_new = 0
    for l in links:
        found = False
        name, url, _ = l.getData()
        for l_old in links_old:
            name_old, url_old, date_old = l_old.getData()
            if l.isEqual(name_old, url_old):
                l.setDate(date_old)
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
        for l in links:
            name, url, date = l.getData()
            mail_text += "[{}] {}\n{}\n\n".format(
                (makePrettyDate(date) if date != None else "NEU"),
                name,
                url
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

        # Save this query for the next time.
        storeQuery(DB_FILE, links)

    else:
        print("Nothing to do. Good-bye!")


if __name__ == "__main__":
    main()