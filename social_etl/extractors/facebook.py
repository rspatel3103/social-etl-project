import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from datetime import datetime, timedelta
from typing import Dict, Any
from helpers import get_access_token

def fetch_insights() -> Dict[str, Any]:
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    access_token = get_access_token("facebook")

    if not page_id or not access_token:
        print("⚠️ FACEBOOK_PAGE_ID or FACEBOOK_ACCESS_TOKEN not set. Returning zeros.")
        return {
            "reach": 0,
            "profile_views": 0,
            "accounts_engaged": 0,
            "website_clicks": 0,
            "total_interactions": 0
        }

    # Step 1: Try page-level metrics for reach and profile_views
    page_metrics = {
        "reach": 0,
        "profile_views": 0
    }
    metrics_url = f"https://graph.facebook.com/v19.0/{page_id}/insights"
    metrics_params = {
        "access_token": access_token,
        "metric": "page_impressions_unique,page_views_total",
        "period": "day"
    }
    try:
        insights_resp = requests.get(metrics_url, params=metrics_params, timeout=15)
        insights_resp.raise_for_status()
        insights_data = insights_resp.json().get("data", [])
        for item in insights_data:
            name = item.get("name")
            value = item.get("values", [{}])[0].get("value", 0)
            if name == "page_impressions_unique":
                page_metrics["reach"] = int(value)
            elif name == "page_views_total":
                page_metrics["profile_views"] = int(value)
    except Exception as e:
        print(f"⚠️ Failed to fetch page-level metrics: {e}")

    # Step 2: Get recent posts and post-level interactions
    posts_url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    posts_params = {
        "access_token": access_token,
        "fields": "id,created_time",
        "limit": 5
    }

    try:
        posts_resp = requests.get(posts_url, params=posts_params, timeout=15)
        posts_resp.raise_for_status()
        posts_data = posts_resp.json().get("data", [])
    except Exception as e:
        print(f"❌ Failed to fetch posts: {e}")
        return {
            **page_metrics,
            "accounts_engaged": 0,
            "website_clicks": 0,
            "total_interactions": 0
        }

    total_reactions = 0
    total_comments = 0
    total_shares = 0
    posts_with_engagement = 0

    for post in posts_data:
        post_id = post.get("id")
        if not post_id:
            continue

        post_fields_url = f"https://graph.facebook.com/v19.0/{post_id}"
        post_fields_params = {
            "access_token": access_token,
            "fields": "reactions.summary(true),comments.summary(true),shares"
        }

        try:
            post_resp = requests.get(post_fields_url, params=post_fields_params, timeout=15)
            post_resp.raise_for_status()
            post_info = post_resp.json()

            reactions = post_info.get("reactions", {}).get("summary", {}).get("total_count", 0)
            comments = post_info.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = post_info.get("shares", {}).get("count", 0)

            if reactions or comments or shares:
                posts_with_engagement += 1

            total_reactions += reactions
            total_comments += comments
            total_shares += shares

        except Exception as e:
            print(f"⚠️ Failed to fetch engagement for post {post_id}: {e}")
            continue

    return {
        "reach": page_metrics["reach"],
        "profile_views": page_metrics["profile_views"],
        "accounts_engaged": posts_with_engagement,
        "website_clicks": 0,
        "total_interactions": total_reactions + total_comments + total_shares
    }
