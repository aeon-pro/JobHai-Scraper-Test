from playwright.sync_api import sync_playwright


def get_html(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            screen={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            color_scheme="light",
            reduced_motion="no-preference",
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",
            },
        )

        page = context.new_page()

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        page.wait_for_load_state("load")

        html = page.content()

        browser.close()
        return html


if __name__ == "__main__":
    html = get_html("https://www.jobhai.com/jobs-in-jaipur-cty")
    print(html)