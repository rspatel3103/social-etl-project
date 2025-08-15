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
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple


import requests
from requests import Response
try:
    # OAuth1 is only needed when user-context credentials are provided. Import
    # lazily so that environments without requests_oauthlib can still use
    # bearer-token mode. If the import fails, we will fall back to bearer
    # authentication later.
    from requests_oauthlib import OAuth1  # type: ignore
except ImportError:
    OAuth1 = None  # type: ignore



def _resolve_user_id(username: str, bearer_token: str) -> Optional[str]:
    """Resolve a Twitter/X username to a numeric user ID using the User Lookup API.


    Tries both the legacy api.twitter.com and the newer api.x.com domains for
    compatibility. Returns ``None`` if the user cannot be resolved.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {"user.fields": "id"}
    candidates = [
        f"https://api.twitter.com/2/users/by/username/{username}",
        f"https://api.x.com/2/users/by/username/{username}",
    ]
    for url in candidates:
        try:
            resp: Response = requests.get(url, headers=headers, params=params, timeout=30)
            if 200 <= resp.status_code < 300:
                data = resp.json()
                return data.get("data", {}).get("id")
            # If the server returns a non-success status, do not retry on that domain
        except Exception:
            # try the next domain
            continue
    return None




def _get_today_window() -> Tuple[str, str]:
    """Return ISO 8601 strings for the start and end of the current day (UTC).


    Returns
    -------
    tuple of str
        (start_time, end_time) in ISO 8601 with Z suffix. The start_time is
        inclusive and the end_time is inclusive.
    """
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc) - timedelta(seconds=1)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")




def _fetch_daily_tweets(
    user_id: str,
    auth: Optional[OAuth1] = None,
    bearer_token: Optional[str] = None,
    max_results: int = 100,
) -> list[dict]:
    
    start_time, end_time = _get_today_window()
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "max_results": max_results,
        "tweet.fields": "public_metrics,organic_metrics,non_public_metrics",
    }
    headers = None
    if bearer_token:
        headers = {"Authorization": f"Bearer {bearer_token}"}


    endpoints = [
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        f"https://api.x.com/2/users/{user_id}/tweets",
    ]
    last_exception: Optional[Exception] = None
    for url in endpoints:
        try:
            if auth:
                resp = requests.get(url, params=params, auth=auth, timeout=30)
            else:
                resp = requests.get(url, params=params, headers=headers, timeout=30)
            # If the server returns an error status, treat it as failure
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) or []
        except Exception as exc:
            # Save the exception and try the next domain
            last_exception = exc
            continue
    # If we get here, all attempts failed
    raise last_exception or RuntimeError("Unknown error fetching tweets")




def _aggregate_metrics(tweets: list[dict]) -> Dict[str, int]:
    """Aggregate metrics across a list of tweets.


    Parameters
    ----------
    tweets : list of dict
        A list of tweet objects returned from the API.


    Returns
    -------
    dict
        A dictionary with keys: reach, profile_views, accounts_engaged,
        website_clicks, total_interactions.
    """
    total_reach = 0
    total_profile_views = 0
    total_website_clicks = 0
    total_interactions = 0
    engaged_posts = 0
    for tweet in tweets:
        non_public = tweet.get("non_public_metrics") or {}
        organic = tweet.get("organic_metrics") or {}
        public = tweet.get("public_metrics") or {}


        # impressions (reach)
        impressions = 0
        if "impression_count" in non_public:
            impressions = non_public.get("impression_count", 0)
        elif "impression_count" in organic:
            impressions = organic.get("impression_count", 0)
        else:
            impressions = public.get("impression_count", 0) or 0
        total_reach += impressions if impressions else 0


        # profile views (user_profile_clicks)
        profile_clicks = 0
        if "user_profile_clicks" in non_public:
            profile_clicks = non_public.get("user_profile_clicks", 0)
        elif "user_profile_clicks" in organic:
            profile_clicks = organic.get("user_profile_clicks", 0)
        total_profile_views += profile_clicks if profile_clicks else 0


        # website clicks (url_link_clicks)
        url_clicks = 0
        if "url_link_clicks" in non_public:
            url_clicks = non_public.get("url_link_clicks", 0)
        elif "url_link_clicks" in organic:
            url_clicks = organic.get("url_link_clicks", 0)
        total_website_clicks += url_clicks if url_clicks else 0


        # interactions (likes, replies, retweets, quote tweets)
        like_count = 0
        reply_count = 0
        retweet_count = 0
        quote_count = 0
        # prefer organic metrics if available, else use public metrics
        if organic:
            like_count = organic.get("like_count", 0)
            reply_count = organic.get("reply_count", 0)
            retweet_count = organic.get("retweet_count", 0)
            quote_count = organic.get("quote_count", 0)
        else:
            like_count = public.get("like_count", 0)
            reply_count = public.get("reply_count", 0)
            retweet_count = public.get("retweet_count", 0)
            quote_count = public.get("quote_count", 0)
        interactions = (like_count or 0) + (reply_count or 0) + (retweet_count or 0) + (quote_count or 0)
        total_interactions += interactions
        if interactions or profile_clicks or url_clicks:
            engaged_posts += 1
    return {
        "reach": int(total_reach),
        "profile_views": int(total_profile_views),
        "accounts_engaged": int(engaged_posts),
        "website_clicks": int(total_website_clicks),
        "total_interactions": int(total_interactions),
    }




def fetch_insights() -> Dict[str, Any]:
   
    # Load environment variables
    bearer_token = os.getenv("X_BEARER_TOKEN")
    api_key = os.getenv("X_API_KEY") or os.getenv("X_CONSUMER_KEY")
    api_secret = os.getenv("X_API_SECRET") or os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("X_ACCESS_SECRET")
    user_id = os.getenv("X_USER_ID")
    username = os.getenv("X_USERNAME")


    # Determine user ID if not provided
    if not user_id:
        if not username:
            raise ValueError(
                "X_USER_ID or X_USERNAME must be set to identify the account"
            )
        if not bearer_token:
            raise ValueError(
                "X_BEARER_TOKEN is required to resolve a username to a user ID"
            )
        user_id = _resolve_user_id(username, bearer_token)
        if not user_id:
            raise RuntimeError(f"Unable to resolve user ID for username '{username}'")


    # Determine authentication method
    auth = None
    if api_key and api_secret and access_token and access_secret and OAuth1:
        # Construct OAuth1 object only if requests_oauthlib is available. If
        # OAuth1 is None (import failed), we cannot use user-context and
        # will fall back to bearer-only mode.
        try:
            auth = OAuth1(api_key, api_secret, access_token, access_secret)  # type: ignore
        except Exception:
            auth = None


    # Fetch tweets for the current day; propagate exceptions on failure
    tweets = _fetch_daily_tweets(
        user_id=user_id,
        auth=auth,
        bearer_token=bearer_token,
    )


    # Aggregate metrics across the tweets
    return _aggregate_metrics(tweets)