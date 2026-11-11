import re
import json
import hashlib
import html
from pathlib import Path
from datetime import datetime, timezone, timedelta

import feedparser

# Official RSS sources
FEEDS = [
    {
        "name": "Press Information Bureau",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"
    },
    {
        "name": "Income Tax Department Recruitment",
        "url": "https://www.incometaxindia.gov.in/hi/recruitment-notices-rss-feed"
    }
]

KEYWORDS = [
    "recruitment", "vacancy", "vacancies", "job",
    "government jobs", "notification", "admit card",
    "result", "answer key", "examination",
    "भर्ती", "रिक्त पद", "नौकरी", "प्रवेश पत्र",
    "परिणाम", "परीक्षा", "आवेदन"
]

def clean(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def quote_yaml(value):
    return json.dumps(str(value), ensure_ascii=False)

def get_category(text):
    text = text.lower()

    if "admit card" in text or "प्रवेश पत्र" in text:
        return "Admit Card"
    if "answer key" in text:
        return "Answer Key"
    if "result" in text or "परिणाम" in text:
        return "Results"
    if "admission" in text:
        return "Admission"
    return "Latest Jobs"

def get_date(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")

    if parsed:
        from time import mktime
        return datetime.fromtimestamp(
            mktime(parsed), timezone.utc
        ).astimezone().strftime("%Y-%m-%d")

    return datetime.now().strftime("%Y-%m-%d")

def make_slug(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return slug.strip("-")[:90] or hashlib.md5(
        title.encode()
    ).hexdigest()[:12]

def create_draft(entry, source):
    title = clean(entry.get("title"))
    link = clean(entry.get("link"))
    summary = clean(entry.get("summary", ""))

    if not title or not link:
        return False

    combined = (title + " " + summary).lower()

    if not any(word in combined for word in KEYWORDS):
        return False

    date = get_date(entry)
    category = get_category(combined)

    folder = Path("_drafts")
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"{date}-{make_slug(title)}.md"
    filepath = folder / filename

    if filepath.exists():
        return False

    content = f"""---
title: {quote_yaml(title)}
date: {date}
category: {category}
organization: {quote_yaml(source)}
source_url: {quote_yaml(link)}
notification_url: ""
apply_url: ""
draft_status: review_required
---

## सूचना

{summary or "इस अपडेट का विवरण आधिकारिक स्रोत पर देखें।"}

**मूल स्रोत:** [{source}]({link})

## महत्वपूर्ण निर्देश

- आधिकारिक नोटिफिकेशन की जाँच करें।
- पदों की संख्या और योग्यता सत्यापित करें।
- आवेदन की अंतिम तारीख जाँचें।
- आवेदन लिंक की पुष्टि करें।
- सत्यापन के बाद ही इसे प्रकाशित करें।

**स्थिति: Draft - अभी प्रकाशित न करें।**
"""

    filepath.write_text(content, encoding="utf-8")
    print(f"Draft created: {filepath}")
    return True

def main():
    total = 0

    for source in FEEDS:
        print("Checking:", source["name"])

        try:
            feed = feedparser.parse(source["url"])

            if feed.bozo and not feed.entries:
                print("Feed could not be read:", source["name"])
                continue

            for entry in feed.entries:
                if create_draft(entry, source["name"]):
                    total += 1

        except Exception as error:
            print("Error:", source["name"], error)

    print("Total new drafts:", total)

if __name__ == "__main__":
    main()
  
