
import re
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SOURCES = [
    {
        "name": "MPESB",
        "url": "https://esb.mp.gov.in/student_dashboard.htm"
    },
    {
        "name": "SSC",
        "url": "https://ssc.gov.in/"
    },
    {
        "name": "UPSC",
        "url": "https://cms.upsc.gov.in/active-examinations/"
    },
    {
        "name": "Railway RRB",
        "url": "https://rrb.indianrailways.gov.in/"
    }
]

KEYWORDS = [
    "recruitment", "vacancy", "notification",
    "admit card", "result", "answer key",
    "examination", "exam", "application",
    "apply online", "employment notice",
    "syllabus", "response sheet", "shortlist",
    "selection", "corrigendum", "calendar"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SarkariJobAlert/1.0)"
}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def fetch_page(url):
    for attempt in range(1, 4):
        try:
            print(f"Connecting: {url} (Attempt {attempt}/3)")

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=(20, 60)
            )

            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as error:
            print("Connection error:", error)

            if attempt < 3:
                time.sleep(15)

    print("Website unavailable:", url)
    return None


def get_category(text):
    text = text.lower()

    if "admit card" in text or "hall ticket" in text:
        return "Admit Card"

    if "result" in text:
        return "Results"

    if "answer key" in text or "response sheet" in text:
        return "Answer Key"

    if any(word in text for word in [
        "recruitment", "vacancy", "notification",
        "apply online", "employment notice"
    ]):
        return "Latest Jobs"

    return "Latest Updates"


def create_draft(folder, source, label, link, context):
    unique_key = source + link

    key = hashlib.md5(
        unique_key.encode("utf-8")
    ).hexdigest()[:12]

    filepath = folder / f"{source.lower().replace(' ', '-')}-{key}.md"

    if filepath.exists():
        return False

    today = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).date().isoformat()

    title = clean(label) or clean(context)[:100]

    if not title:
        title = "Official Government Update"

    content = f"""---
title: {json.dumps(source + " - " + title, ensure_ascii=False)}
date: {today}
category: {json.dumps(get_category(title + " " + context), ensure_ascii=False)}
organization: {json.dumps(source, ensure_ascii=False)}
source_url: {json.dumps(link, ensure_ascii=False)}
draft_status: review_required
---

## {source} Official Update

**सूचना:** {title}

### आधिकारिक वेबसाइट से उपलब्ध जानकारी

{context}

### महत्वपूर्ण लिंक

[आधिकारिक लिंक खोलें]({link})

**सत्यापन:** इस सूचना की अंतिम तिथि, पात्रता, पदों की संख्या और अन्य विवरण आधिकारिक नोटिस से जाँचें।

**स्थिति: Draft - आपकी मंजूरी के बिना प्रकाशित नहीं करें।**
"""

    filepath.write_text(content, encoding="utf-8")

    print("Draft created:", filepath)
    return True


def process_source(source, folder):
    print("\nChecking:", source["name"])

    html = fetch_page(source["url"])

    if html is None:
        print("Skipping this source.")
        return 0

    soup = BeautifulSoup(html, "html.parser")
    total = 0
    seen = set()

    for a in soup.find_all("a", href=True):
        label = clean(a.get_text(" ", strip=True))

        parent = a.find_parent(["tr", "li", "p", "div"])

        context = clean(
            parent.get_text(" ", strip=True)
            if parent else label
        )

        combined = (label + " " + context).lower()

        if not any(word in combined for word in KEYWORDS):
            continue

        link = urljoin(source["url"], a["href"])

        if not link.startswith("http"):
            continue

        if link in seen:
            continue

        seen.add(link)

        if create_draft(
            folder,
            source["name"],
            label,
            link,
            context[:1200]
        ):
            total += 1

    print(source["name"], "new drafts:", total)
    return total


def main():
    folder = Path("_drafts")
    folder.mkdir(exist_ok=True)

    total = 0

    for source in SOURCES:
        try:
            total += process_source(source, folder)

        except Exception as error:
            print("Source processing error:", source["name"], error)
            continue

    print("\n--------------------------------")
    print("Total new drafts:", total)
    print("All drafts require manual review.")
    print("--------------------------------")


if __name__ == "__main__":
    main()
