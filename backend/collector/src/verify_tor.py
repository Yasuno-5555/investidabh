import asyncio
import os
import sys
from playwright.async_api import async_playwright
from tor_control import renew_tor_identity

# Configuration
PROXY_HOST = os.getenv("PROXY_HOST", "tor")
PROXY_PORT = os.getenv("PROXY_PORT", "9050")
PROXY_SERVER = f"socks5://{PROXY_HOST}:{PROXY_PORT}"
TOR_CONTROL_HOST = os.getenv("TOR_CONTROL_HOST", "tor")
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))

async def get_ip_info(context_name):
    print(f"[*] [{context_name}] Checking IP...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": PROXY_SERVER}
        )
        context = await browser.new_context(
             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # 1. Check Tor Project
            await page.goto("https://check.torproject.org/", timeout=60000)
            text = await page.inner_text("body")
            
            is_tor = "Congratulations. This browser is configured to use Tor" in text
            print(f"[{context_name}] Tor Check: {'PASS' if is_tor else 'FAIL'}")
            if not is_tor:
                print(f"[{context_name}] Warning: check.torproject.org did not confirm Tor usage!")

            # 2. Get IP
            ip_element = await page.query_selector("strong")
            ip_address = await ip_element.inner_text() if ip_element else "Unknown"
            print(f"[{context_name}] Current IP: {ip_address}")
            return ip_address
            
        except Exception as e:
            print(f"[{context_name}] Error: {e}")
            return None
        finally:
            await browser.close()

async def main():
    print(f"--- Verify Tor Integration (Proxy: {PROXY_SERVER}) ---")
    
    # 1. First IP Check
    ip1 = await get_ip_info("Initial Identity")
    if not ip1:
        print("[!] Failed to get initial IP. Is Tor container running?")
        sys.exit(1)
        
    # 2. Rotate Identity
    print("\n[*] Rotating Identity...")
    success = await renew_tor_identity(TOR_CONTROL_HOST, TOR_CONTROL_PORT)
    if not success:
        print("[!] Rotation failed.")
        sys.exit(1)
        
    # 3. Second IP Check
    ip2 = await get_ip_info("New Identity")
    if not ip2:
        print("[!] Failed to get new IP.")
        sys.exit(1)
        
    # 4. Verification
    print("\n--- Result ---")
    if ip1 != ip2:
        print(f"[SUCCESS] IP changed from {ip1} to {ip2}")
    else:
        print(f"[WARNING] IP did NOT change. (Note: Tor sometimes reuses exits or rotation takes time)")

if __name__ == "__main__":
    asyncio.run(main())
