import hashlib

# Maintain Idempotency
def make_event_id(listing_id: str, scraped_at: str) -> str:
    return hashlib.md5(f"{listing_id}-{scraped_at}".encode()).hexdigest()