"""Fetch play_count from IG media info API for a shortcode using the authenticated browser profile."""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

SHORTCODE = sys.argv[1] if len(sys.argv) > 1 else 'DXajE68EWNA'
PROFILE_DIR = r'C:\Users\feedp\ig_browser_profile'

def shortcode_to_id(sc):
    alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    n = 0
    for c in sc:
        n = n * 64 + alpha.index(c)
    return str(n)

async def main():
    media_id = shortcode_to_id(SHORTCODE)
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=True, channel='chrome',
            args=['--disable-blink-features=AutomationControlled'],
        )
        page = await ctx.new_page()
        await page.goto(f'https://www.instagram.com/p/{SHORTCODE}/', wait_until='domcontentloaded')
        await page.wait_for_timeout(2500)
        data = await page.evaluate(f"""async () => {{
            const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
            const r = await fetch('https://www.instagram.com/api/v1/media/{media_id}/info/', {{
                headers: {{'x-ig-app-id': '936619743392459', 'x-csrftoken': csrf}},
                credentials: 'include'
            }});
            return await r.json();
        }}""")
        item = (data.get('items') or [{}])[0]
        out = {
            'shortcode': SHORTCODE,
            'play_count': item.get('play_count'),
            'view_count': item.get('view_count'),
            'fb_play_count': item.get('fb_play_count'),
            'video_view_count': item.get('video_view_count'),
            'ig_play_count': item.get('ig_play_count'),
            'like_count': item.get('like_count'),
            'comment_count': item.get('comment_count'),
            'uploader': (item.get('user') or {}).get('username'),
        }
        print(json.dumps(out, indent=2))
        await ctx.close()

asyncio.run(main())
