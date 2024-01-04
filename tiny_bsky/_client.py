import requests
import configparser
from datetime import datetime, timezone
import time
import json

FETCH_LIMIT = 100


class ClientError(Exception):
    def __init__(self, json_message):
        self._json_message = json_message

    def __str__(self):
        return json.dumps(self._json_message, indent=2)


class Client(object):
    def __init__(self, user_id=None, password=None, ini_file=None):
        if user_id is None and password is None:
            config = configparser.ConfigParser()
            config.read(ini_file, encoding="utf-8")
            user_id = config["bsky"]["user"]
            password = config["bsky"]["password"]
        r = requests.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": user_id, "password": password},
        )
        if r.status_code != 200:
            raise ClientError(r.json())
        self._session = r.json()

    def post(self, text):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        post = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": now,
        }

        accessjwt = self._session["accessJwt"]
        did = self._session["did"]
        r = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": "Bearer " + accessjwt},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": post,
            },
        )
        return r.json()

    def getMentions(self, after_time=None):
        accessjwt = self._session["accessJwt"]
        params = {"limit": FETCH_LIMIT}
        mentions = []
        while True:
            r = requests.get(
                "https://bsky.social/xrpc/app.bsky.notification.listNotifications",
                headers={"Authorization": "Bearer " + accessjwt},
                params=params,
            )
            rjson = r.json()
            done = False
            for x in rjson["notifications"]:
                record = x["record"]
                if after_time is not None and record["createdAt"] <= after_time:
                    done = True
                    break
                if x["reason"] == "mention":
                    mentions.append(x)
            time.sleep(1)
            if done or "cursor" not in rjson:
                break
            params = {"limit": FETCH_LIMIT, "cursor": rjson["cursor"]}
        return mentions
