# database/db_manager.py
import json
import os
from typing import List, Dict

DB_PATH = "data/articles.json"

def load_articles() -> List[Dict]:
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_articles(articles: List[Dict]):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def article_exists(url: str) -> bool:
    articles = load_articles()
    return any(article["url"] == url for article in articles)

def add_article(new_article: Dict):
    articles = load_articles()
    if not article_exists(new_article["url"]):
        articles.append(new_article)
        save_articles(articles)
        return True
    return False
