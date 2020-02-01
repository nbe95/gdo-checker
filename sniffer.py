#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from time import sleep
import json

CONFIG_FILE = "./config.json"


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


def main():
    # Read config.
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    # Query URL and extract PDF links.
    content = getContents(config["url"])
    links = extractPdfs(content)
    total_links = len(links)

    # Check if there are new links.
    new_links = total_links

    print("There are {} new PDF links of {} total on \"{}\".".format(
        new_links,
        total_links,
        config["url"]
    ))

    if new_links > 0:
        # Make subject and message text.
        mail_subject = "Kevelaer: {} neue Gottesdienstpläne".format(new_links)

        mail_text = "Hallo {name},\n\n"
        mail_text += "es wurden kürzlich neue Gottesdienstpläne für St. Marien Kevelaer veröffentlicht.\n\n"
        for (name, link) in links:
            mail_text += "[{}] {}\n{}\n\n".format(
                "NEU",
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
            sleep(5)
    else:
        print("Nothing to do. Good-bye!")


if __name__ == "__main__":
    main()