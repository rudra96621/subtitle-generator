from pymongo import MongoClient
import gridfs
from urllib.parse import quote_plus
import os

def get_connection():
    # Prefer full URI in secrets or env
    explicit_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DATABASE", "subtitleApp")
    if explicit_uri:
        uri = explicit_uri
    else:
        username = os.getenv("MONGODB_USERNAME", "rudra")
        raw_password = os.getenv("MONGODB_PASSWORD", "Rudra@123")
        if not isinstance(raw_password, str):
            raw_password = str(raw_password) if raw_password is not None else ""
        try:
            password = quote_plus(raw_password)
        except Exception:
            password = ""
        cluster_url = os.getenv("MONGODB_CLUSTER_URL", "cluster0.ucw0onm.mongodb.net")
        if not cluster_url or str(cluster_url).strip().lower() in {"none", "null"}:
            print("❌ MONGODB_CLUSTER_URL is missing/invalid. Provide MONGODB_URI or set a valid cluster.")
            return None
        cluster_url = str(cluster_url).strip()
        if cluster_url.startswith("mongodb://") or cluster_url.startswith("mongodb+srv://"):
            uri = cluster_url
            if "/" not in uri.split("@")[-1]:
                uri = f"{uri}/{database_name}"
            if "?" not in uri:
                uri = f"{uri}?retryWrites=true&w=majority"
        else:
            uri = f"mongodb+srv://{username}:{password}@{cluster_url}/{database_name}?retryWrites=true&w=majority"

    try:
        client = MongoClient(uri, tls=True, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[database_name]
        return db
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return None

def get_gridfs():
    db = get_connection()
    return gridfs.GridFS(db)
