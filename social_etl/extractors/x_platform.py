"""
Twitter (X) extractor.

This module defines a stub for fetching engagement metrics from the
Twitter (X) API. The Twitter v2 API exposes endpoints such as
``/2/users/:id/tweets`` and ``/2/tweets/:id`` which can return
impressions and engagement statistics. To use these endpoints you
must register a developer application and generate a Bearer Token or
OAuth2 credentials. Set these in the ``X_BEARER_TOKEN`` (or
``X_API_KEY`` and ``X_API_SECRET``) environment variables.

At the time of writing, Twitter's API terms of service and pricing
structures change frequently. Accordingly this implementation is a
placeholder that returns zeros for all metrics. Integrators should
replace the TODO section with real API calls when they have access to
the required endpoints.
"""

from __future__ import annotations

import os
import requests
from requests_oauthlib import OAuth1
from typing import Dict, Any

def _resolve_user_id(username: str, bearer_token: str) -> str | None:
    """Resolve a Twitter/X username to a numeric user ID using the User Lookup API."""
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {"user.fields": "id"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("id")
    except Exception as exc:
        print(f"⚠️  Failed to resolve X username '{username}' to user ID: {exc}")
        return None

def _fetch_public_metrics(user_id: str, bearer_token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        url = f"https://api.twitter.com/2/users/{user_id}"
        params = {"user.fields": "public_metrics"}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        metrics = data.get("data", {}).get("public_metrics", {})
        return {
            "reach": metrics.get("followers_count", 0),
            "profile_views": 0,  # Not available publicly
            "accounts_engaged": 0,
            "website_clicks": 0,
            "total_interactions": metrics.get("tweet_count", 0)
        }
    except Exception as exc:
        print(f"⚠️  Failed to fetch public metrics: {exc}")
        return {"reach": 0, "profile_views": 0, "accounts_engaged": 0, "website_clicks": 0, "total_interactions": 0}

def _fetch_private_metrics(user_id: str, api_key: str, api_secret: str, access_token: str, access_secret: str) -> Dict[str, Any]:
    auth = OAuth1(api_key, api_secret, access_token, access_secret)
    try:
        url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "tweet.fields": "organic_metrics,non_public_metrics,public_metrics",
            "max_results": 5  # optional: fetch last 5 tweets
        }
        resp = requests.get(url, auth=auth, params=params, timeout=30)
        resp.raise_for_status()
        tweets = resp.json().get("data", [])

        total_reach = 0
        total_views = 0
        total_clicks = 0
        total_interactions = 0
        engaged_tweets = 0  # tracks how many tweets had any engagement

        for tweet in tweets:
            metrics = tweet.get("organic_metrics") or {}

            impressions = metrics.get("impression_count", 0)
            profile_clicks = metrics.get("user_profile_clicks", 0)
            link_clicks = metrics.get("link_clicks", 0)
            likes = metrics.get("like_count", 0)
            replies = metrics.get("reply_count", 0)
            retweets = metrics.get("retweet_count", 0)
            bookmarks = metrics.get("bookmark_count", 0)

            tweet_interactions = likes + replies + retweets + bookmarks

            total_reach += impressions
            total_views += profile_clicks
            total_clicks += link_clicks
            total_interactions += tweet_interactions

            # Count this tweet as "engaged" if it had any non-zero activity
            if any([tweet_interactions, profile_clicks, link_clicks]):
                engaged_tweets += 1

        return {
            "reach": total_reach,
            "profile_views": total_views,
            "accounts_engaged": engaged_tweets,
            "website_clicks": total_clicks,
            "total_interactions": total_interactions + total_clicks
        }
    except Exception as exc:
        print(f"⚠️  Failed to fetch private metrics: {exc}")
        return {"reach": 0, "profile_views": 0, "accounts_engaged": 0, "website_clicks": 0, "total_interactions": 0}

def fetch_insights() -> Dict[str, Any]:
    # Read credentials from environment (.env overrides)
    bearer_token = os.getenv("X_BEARER_TOKEN")
    api_key      = os.getenv("X_API_KEY") or os.getenv("X_CONSUMER_KEY")
    api_secret   = os.getenv("X_API_SECRET") or os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret= os.getenv("X_ACCESS_TOKEN_SECRET")
    user_id      = os.getenv("X_USER_ID")
    username     = os.getenv("X_USERNAME")

    # If only a username is provided, resolve it to a user ID via Bearer token
    if not user_id and username:
        user_id = _resolve_user_id(username, bearer_token)

    # Decide which authentication method to use
    if api_key and api_secret and access_token and access_secret:
        return _fetch_private_metrics(user_id, api_key, api_secret, access_token, access_secret)
    elif bearer_token:
        return _fetch_public_metrics(user_id, bearer_token)
    else:
        print("⚠️  No X credentials supplied…")
        return {"reach": 0, "profile_views": 0, "accounts_engaged": 0, "website_clicks": 0, "total_interactions": 0}
