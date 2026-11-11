
import re
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://esb.mp.gov.in/student_dashboard.htm"


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_website():
    """Try connecting to MPESB website three times."""

    for attempt in range(1, 4):
        try:
            print(f"MPESB connection attempt {attempt}/3")

            response = requests.get(
                URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SarkariJobAlert/1.0)"
                },
                timeout=(20, 60)
            )

            response.raise_for_status()
            print("MPESB website connected successfully.")
            return response

        except requests.exceptions.RequestException as error:
            print("Connection failed:", error)

            if attempt < 3:
                print("Retrying after 15 seconds...")
                time.sleep(15)

    print("MPESB website is currently unavailable.")
    print("No drafts generated. Please try again later.")
    return None


def main():
    folder = Path("_drafts")
    folder.mkdir(exist_ok=True)

    response = get_website()

    if response is None:
        return

    soup = BeautifulSoup(response.text, "html.parser")

    total = 0

    for table in soup.find_all("table"):

        heading = table.find_previous(
            ["li", "h2", "h3", "h4"]
        )

        title = (
            clean(heading.get_text(" ", strip=True))
            if heading else ""
        )

        table_text = clean(
            table.get_text(" ", strip=True)
        )

        if not title:
            continue

        if "2026" not in (title + " " + table_text):
            continue

        links = []

        for a in table.find_all("a", href=True):
            link = urljoin(URL, a["href"])

            label = (
                clean(a.get_text(" ", strip=True))
                or "Official Link"
            )

            if link.startswith("http"):
                links.append((label, link))

        if not links:
            continue

        unique_links = list(dict.fromkeys(links))

        key = hashlib.md5(
            (title + str(unique_links)).encode("utf-8")
        ).hexdigest()[:12]

        filepath = folder / f"mpesb-2026-{key}.md"

        if filepath.exists():
            print("Already exists:", filepath)
            continue

        today = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).date().isoformat()

        content = f"""---
title: {json.dumps("MPESB - " + title, ensure_ascii=False)}
date: {today}
category: Latest Jobs
organization: "MPESB"
source_url: "{URL}"
draft_status: review_required
---

## MPESB Official Update

**परीक्षा:** {title}

### आधिकारिक वेबसाइट पर उपलब्ध जानकारी

{table_text}

### महत्वपूर्ण लिंक

""" + "\n".join(
            f"- [{label}]({link})"
            for label, link in unique_links
        ) + """

**स्थिति: Draft - सत्यापन के बाद ही प्रकाशित करें।**
"""

        filepath.write_text(
            content,
            encoding="utf-8"
        )

        total += 1

        print("Draft created:", filepath)

    print("--------------------------------")
    print("Total new drafts:", total)
    print("Drafts require manual verification.")
    print("--------------------------------")


if __name__ == "__main__":
    main()
    
