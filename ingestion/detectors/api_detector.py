import asyncio
from playwright.async_api import async_playwright

# Change this to any real estate page you want to analyze
TARGET_URL = "https://www.realtor.com/international/au/sydney-nsw/"

# Keywords commonly found in real data APIs
API_KEYWORDS = [
    "graphql",
    "search",
    "listing",
    "listings",
    "property",
    "properties",
    "homes",
    "results",
    "api"
]

# Things we want to ignore (ads, analytics, assets)
IGNORE_KEYWORDS = [
    "_next",
    "static",
    "chunk",
    "pixel",
    "sync",
    "analytics",
    "ads",
    "doubleclick",
    "rubiconproject",
    "criteo",
    "tapad",
    "scorecardresearch",
    "lijit",
    "pubmatic",
    "adnxs",
    "smartadserver",
    "onaudience",
    "openx",
    "bidswitch",
    "googleads",
    "cookie",
]


def is_real_api(url: str):
    """
    Determine if a network request is likely a real API endpoint.
    """

    url = url.lower()

    # Ignore ad-tech and assets
    if any(bad in url for bad in IGNORE_KEYWORDS):
        return False

    # Look for API patterns
    if any(good in url for good in API_KEYWORDS):
        return True

    return False


async def detect_apis():

    discovered = {}

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context()

        page = await context.new_page()

        print(f"\nScanning: {TARGET_URL}\n")

        async def handle_response(response):

            url = response.url.lower()

            # GraphQL detection (important)
            if "graphql" in url:
                print("\nGRAPHQL API FOUND:\n")
                print(url)
                discovered[url] = 999999
                return

            if not is_real_api(url):
                return

            try:
                body = await response.text()
                size = len(body)

                # Filter very small responses
                if size < 1500:
                    return

                discovered[url] = size

            except:
                pass

        page.on("response", handle_response)

        # Load page
        await page.goto(TARGET_URL)

        # Scroll page to trigger lazy-loaded requests
        for _ in range(6):
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(1)

        await asyncio.sleep(5)

        await browser.close()

    print("\nPossible Listing APIs:\n")

    for url, size in sorted(discovered.items(), key=lambda x: x[1], reverse=True):
        print(f"{url}  (response size: {size})")


if __name__ == "__main__":
    asyncio.run(detect_apis())