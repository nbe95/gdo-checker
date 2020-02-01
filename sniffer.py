#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import urllib.request
import re
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


def main():
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    content = getContents(config["url"])
    files = extractPdfs(content)

    print(files)


if __name__ == "__main__":
    main()