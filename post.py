"""
Check sheet every 4, 24 and 48 hours to update rows
"""

import json
import time
import html

import gspread
import requests
import redis
import praw
from oauth2client.service_account import ServiceAccountCredentials

def agent_headers():
    agent_name = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
    return {'User-Agent': agent_name,'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8','Accept-Language':'en-US,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch, br'}

redis_host = "localhost"
redis_port = 6379
redis_password = ""

r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('Document Editing Rescan-7d7d0fac1720.json', scope)
client = gspread.authorize(creds)

reddit = praw.Reddit("bot2")

def check(subreddit_name, title, user_name):
    """
    Check if a post is hidden from
    a subreddit
    """
    is_hidden = "Hidden"
    sub = reddit.subreddit(subreddit_name)
    new_title = html.unescape(title)
    for submission in sub.search(new_title):
        ttle = str(submission.title)
        if ttle.lower() == new_title.lower() and submission.author == str(user_name):
            is_hidden = "Okay"
            break
    return is_hidden

def needed_names(link, key):
    """
    Get username, post title, numbers of upvote
    subreddit name from a post
    """
    post = requests.get(link, headers=agent_headers())
    to_json = json.loads(post.text)
    try:
        values_list = sheet.row_values(key)
        title = values_list[5]
    except:
        return "", "", "", ""
    user_name = values_list[10]
    subreddit_name = to_json[0]["data"]["children"][0]["data"]["subreddit"]
    upvotes = to_json[0]["data"]["children"][0]["data"]["score"]
    return title, user_name, subreddit_name, upvotes

row_numbers = []
sheet = client.open("Reddit operating sheet request").sheet1
for key in r.scan_iter():
     if "freeland" not in key:
        extract = json.loads(r.get(key))
        now = time.time()
        # If the post row on sheet is 4 hours old
        if int(now - extract["key"][1]) >= 14400:
            if int(now - extract["key"][1]) <= 16662:
                title, user_name, subreddit_name, _ = needed_names(f"{extract['key'][2]}.json", extract["key"][0])
                try:
                    is_hidden = check(subreddit_name, title, user_name)
                    sheet.update_cell(extract["key"][0], 12, f"{is_hidden}")
                except:
                    r.delete(key)
                    continue
        # If the post row on sheet is 24 hours old
        if int(now - extract["key"][1]) >= 86400:
            if int(now - extract["key"][1]) <= 88662:
                title, user_name, subreddit_name, upvotes = needed_names(f"{extract['key'][2]}.json", extract["key"][0])
                try:
                    is_hidden = check(subreddit_name, title, user_name)
                    sheet.update_cell(extract["key"][0], 4, f"{upvotes}")
                    sheet.update_cell(extract["key"][0], 13, f"{is_hidden}")
                except:
                    r.delete(key)
                    continue
        # If the post row on sheet is 48 hours old
        if int(now - extract["key"][3]) >= 172800:
            submission = reddit.submission(url=extract["key"][2])
            try:
                sheet.update_cell(extract["key"][0], 5, len(submission.comments))
            except:
                r.delete(key)
                continue
            value = sheet.acell("A"f"{extract['key'][0]}", value_render_option='FORMULA').value
            lst = value.split('"')
            try:
                sheet_three = client.open_by_url(str(lst[1])).sheet1
                values_list = sheet.row_values(extract["key"][0])
                values_list_edited = [""]
                for i in range(1, len(values_list)):
                    values_list_edited.append(values_list[i])
                sheet_three.append_row(values_list_edited)
                r.delete(key)
            except:
                r.delete(key)