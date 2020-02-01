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


def getContents(url):
    page = urllib.request.urlopen(url)
    return page


def extractPdfs(content, parser = "html.parser"):
    soup = BeautifulSoup(content, parser)
    main_content = str(soup.select("div#main")[0])

    soup = BeautifulSoup(main_content, parser)
    links = soup.find_all("a")

    pdfs = []
    for l in links:
        title = l.get_text()
        href = l.get("href")
        if href.endswith(".pdf"):
            pdfs.append((title, href))
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


def compareLinks(query, last_query):
    total_files = new_files = 0
    links_with_date = []
    for (name, link) in query:
        total_files += 1
        found = False
        for (name_old, link_old, date_old) in last_query:
            if name == name_old and link == link_old:
                links_with_date.append((name, link, date_old))
                found = True
                break
        if not found:
            new_files += 1
            links_with_date.append((name, link, None))

    return (links_with_date, new_files, total_files)


def storeQuery(file, query):
    with open(file, "w") as f:
        writer = csv.writer(f, delimiter = ",", quotechar = "\"", quoting = csv.QUOTE_MINIMAL)
        for name, link, date in query:
            date_str = datetime.datetime.strftime(
                date if date != None else datetime.datetime.today(),
                "%Y-%m-%d"
            )
            writer.writerow([name, link, date_str])


def loadQuery(file):
    query = []
    try:
        f = open(file, "r")
    except: # no query file yet
        return query

    reader = csv.reader(f, delimiter = ",", quotechar = "\"")
    for name, link, date_str in reader:
        query.append((name, link, datetime.datetime.strptime(date_str, "%Y-%m-%d")))
    return query


def makeDateString(date):
    if date == None:
        return "NEU"
    diff = (datetime.datetime.today() - date).days
    return "seit {} {}".format(
        diff,
        "Tag" if diff == 1 else "Tagen"
    )


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
    for name, link, date in links_old:
        print("  - [{}] \"{}\" -> {}".format(
            date.strftime("%Y-%m-%d"),
            name,
            link
        ))

    # Query URL and extract PDF links.
    content = getContents(config["url"])
    links = extractPdfs(content)
    print("URL query of \"{}\" ({} entries) finished.".format(
        config["url"],
        len(links)
    ))
    for name, link in links:
        print("  - \"{}\" -> {}".format(
            name,
            link
        ))

    # Check if there are new links.
    links_with_date, new_links, total_links = compareLinks(links, links_old)

    print("There are {} new PDF links of {} total.".format(
        new_links,
        total_links
    ))

    if new_links > 0:
        # Make subject and message text.
        mail_subject = "Kevelaer: {} {}".format(
            new_links,
            "neuer Gottesdienstplan" if new_links == 1 else "neue Gottesdienstpläne"
        )

        mail_text = "Hallo {name},\n\n"
        mail_text += "es wurden kürzlich neue Gottesdienstpläne für St. Marien Kevelaer veröffentlicht.\n\n"
        for (name, link, date) in links_with_date:
            mail_text += "[{}] {}\n{}\n\n".format(
                makeDateString(date),
                name,
                link
            )
        mail_text += "\nViele Grüße\ndein Raspberry Pi\n"

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
        storeQuery(DB_FILE, links_with_date)

    else:
        print("Nothing to do. Good-bye!")


if __name__ == "__main__":
    main()