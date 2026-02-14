"""
Lead Discovery Client - Interacts with the hosted B2B Lead Discovery Agent.

Uses Playwright to open the hosted dashboard (Vercel + Render backend),
type queries, wait for results, and scrape them.

Dashboard: https://agent-three-eta.vercel.app/
Backend is connected via Render — no local server needed.
"""

import asyncio
import threading
import time
import webbrowser
from typing import Dict, Any


class LeadDiscoveryClient:
    """
    Browser-based client for the B2B Lead Discovery Agent.
    
    Opens the hosted dashboard in a Playwright browser, submits queries,
    waits for the pipeline to complete, and scrapes results.
    """

    def __init__(self, dashboard_url: str = "https://agent-three-eta.vercel.app", timeout: int = 300):
        self.dashboard_url = dashboard_url.rstrip("/")
        self.timeout = timeout
        self._loop = None
        self._thread = None

    def _ensure_event_loop(self):
        if self._loop is not None and self._loop.is_running():
            return

        def _run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=_run_loop, args=(self._loop,), daemon=True)
        self._thread.start()

    def _run_async(self, coro):
        self._ensure_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self.timeout + 60)

    async def _async_analyze(self, query: str) -> Dict[str, Any]:
        """
        Opens the dashboard in a visible Playwright browser, types the query,
        submits it, waits for results, then scrapes the page.
        """
        from playwright.async_api import async_playwright

        collected = {
            "query": query,
            "results_text": "",
            "companies_found": [],
            "chat_messages": [],
            "errors": [],
            "completed": False,
            "dashboard_url": self.dashboard_url
        }

        url = self.dashboard_url
        print(f"  [Lead Discovery] Opening dashboard at {url}...")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(viewport={"width": 1400, "height": 900})
                page = await context.new_page()

                # Navigate to the hosted dashboard
                await page.goto(url, wait_until="networkidle", timeout=30000)
                print(f"  [Lead Discovery] Dashboard loaded.")

                # Wait for the app to render
                try:
                    await page.wait_for_selector('input[placeholder*="Find"]', timeout=15000)
                    print(f"  [Lead Discovery] UI is ready.")
                except:
                    print(f"  [Lead Discovery] Warning: Input field not found, trying anyway.")

                # Give WebSocket time to connect to Render backend
                await asyncio.sleep(4)

                # Check connection status (green dot = connected)
                connection_dot = await page.query_selector('.bg-green-500')
                if not connection_dot:
                    collected["errors"].append(
                        "Dashboard shows OFFLINE — the Render backend may be sleeping. "
                        "Try again in 30 seconds (Render free tier spins down after inactivity)."
                    )
                    print(f"  [Lead Discovery] ⚠️ Backend not connected, waiting longer...")
                    # Wait more — Render free tier may need to cold start
                    await asyncio.sleep(15)
                    connection_dot = await page.query_selector('.bg-green-500')
                    if connection_dot:
                        print(f"  [Lead Discovery] ✅ Backend connected after cold start.")
                        collected["errors"].clear()
                    else:
                        print(f"  [Lead Discovery] ❌ Backend still offline.")
                        await browser.close()
                        return collected
                else:
                    print(f"  [Lead Discovery] ✅ Connected to Render backend.")

                # Type the query
                input_field = await page.query_selector('input[type="text"]')
                if input_field:
                    await input_field.fill(query)
                    print(f"  [Lead Discovery] Typed query: '{query}'")
                    await asyncio.sleep(0.5)

                    # Submit
                    submit_btn = await page.query_selector('button[type="submit"]')
                    if submit_btn:
                        is_disabled = await submit_btn.get_attribute("disabled")
                        if is_disabled is None:
                            await submit_btn.click()
                            print(f"  [Lead Discovery] Query submitted! Waiting for results...")
                        else:
                            collected["errors"].append("Submit button is disabled.")
                            await browser.close()
                            return collected
                    else:
                        await input_field.press("Enter")
                        print(f"  [Lead Discovery] Submitted via Enter key.")
                else:
                    collected["errors"].append("Could not find input field.")
                    await browser.close()
                    return collected

                # Wait for results — poll until batch_complete or timeout
                start_time = time.time()
                last_message_count = 0

                while True:
                    elapsed = time.time() - start_time
                    if elapsed > self.timeout:
                        collected["errors"].append(f"Timeout after {int(elapsed)}s.")
                        break

                    await asyncio.sleep(5)

                    # Scrape chat messages
                    messages = await page.query_selector_all('.flex.flex-col .p-3.rounded-lg')
                    current_messages = []
                    for msg_el in messages:
                        text = await msg_el.inner_text()
                        if text.strip():
                            current_messages.append(text.strip())

                    if len(current_messages) > last_message_count:
                        new_msgs = current_messages[last_message_count:]
                        for msg in new_msgs:
                            print(f"  [Lead Discovery] 💬 {msg[:120]}")
                        last_message_count = len(current_messages)

                    collected["chat_messages"] = current_messages

                    # Check if batch is complete
                    page_text = await page.inner_text("body")
                    if "Batch analysis complete" in page_text or "Processed" in page_text:
                        collected["completed"] = True
                        print(f"  [Lead Discovery] ✅ Pipeline complete!")
                        break

                    # Check if analyzing spinner is gone (single company done)
                    spinner = await page.query_selector('.animate-spin')
                    if not spinner and elapsed > 30 and len(current_messages) > 1:
                        collected["completed"] = True
                        print(f"  [Lead Discovery] Pipeline appears complete.")
                        break

                    print(f"  [Lead Discovery] ⏳ Waiting... ({int(elapsed)}s/{self.timeout}s)")

                # Final scrape
                await asyncio.sleep(3)

                # Get company buttons from search results
                buttons = await page.query_selector_all('.text-left.text-xs')
                for btn in buttons:
                    try:
                        name_el = await btn.query_selector('.font-medium')
                        context_el = await btn.query_selector('.text-muted-foreground')
                        name = await name_el.inner_text() if name_el else ""
                        context = await context_el.inner_text() if context_el else ""
                        if name:
                            collected["companies_found"].append({"name": name, "context": context})
                    except:
                        pass

                # Click each "View Analysis" button and scrape detailed results with LinkedIn
                result_buttons = await page.query_selector_all('button:has-text("View Analysis")')
                detailed_results = []

                for btn in result_buttons[:5]:
                    try:
                        await btn.click()
                        await asyncio.sleep(2)
                        
                        # Extract structured data using JS evaluation
                        result_data = await page.evaluate('''() => {
                            const panel = document.querySelector('.flex-1.overflow-y-auto');
                            if (!panel) return null;
                            
                            // Get company header info
                            const companyName = panel.querySelector('h2')?.innerText || '';
                            const summary = panel.querySelector('h2')?.closest('div')?.querySelector('p')?.innerText || '';
                            const confidence = panel.querySelector('.text-3xl')?.innerText || '';
                            
                            // Get company details
                            const details = [...panel.querySelectorAll('.grid .flex.items-center')].map(el => el.innerText);
                            
                            // Get ALL LinkedIn URLs and associated info
                            const linkedinLinks = [...panel.querySelectorAll('a[href*="linkedin.com"]')].map(a => ({
                                url: a.href,
                                name: a.innerText.trim()
                            }));
                            
                            // Get email links
                            const emailLinks = [...panel.querySelectorAll('a[href^="mailto:"]')].map(a => ({
                                email: a.href.replace('mailto:', ''),
                                name: a.closest('tr')?.querySelector('td:first-child')?.innerText?.trim() || '',
                                title: a.closest('tr')?.querySelector('td:nth-child(2)')?.innerText?.trim() || ''
                            }));
                            
                            // Get all table rows (contacts)
                            const contacts = [...panel.querySelectorAll('tbody tr')].map(row => {
                                const cells = row.querySelectorAll('td');
                                const linkedinEl = row.querySelector('a[href*="linkedin.com"]');
                                return {
                                    name: cells[0]?.innerText?.trim() || '',
                                    title: cells[1]?.innerText?.trim() || '',
                                    email: cells[2]?.innerText?.trim() || '',
                                    linkedin: linkedinEl?.href || ''
                                };
                            });
                            
                            // Get decision makers (general section)
                            // Note: Can't use .bg-muted/20 as CSS selector (/ is invalid)
                            // Instead, find the "General Decision Makers" section and get its cards
                            const dmSection = [...panel.querySelectorAll('h3')].find(h => h.innerText?.includes('Decision Makers'));
                            const dmContainer = dmSection?.closest('div.rounded-xl');
                            const dmCards = dmContainer ? [...dmContainer.querySelectorAll('.rounded-lg')] : [];
                            const decisionMakers = dmCards.map(el => {
                                const nameEl = el.querySelector('.font-medium');
                                const titleEl = el.querySelector('.text-muted-foreground');
                                const powerEl = el.querySelector('.border-border');
                                const linkedinEl = el.querySelector('a[href*="linkedin.com"]');
                                return {
                                    name: nameEl?.innerText?.trim() || '',
                                    title: titleEl?.innerText?.trim() || '',
                                    power: powerEl?.innerText?.trim() || '',
                                    linkedin: linkedinEl?.href || ''
                                };
                            }).filter(dm => dm.name);
                            
                            return {
                                companyName, summary, confidence, details,
                                linkedinLinks, emailLinks, contacts, decisionMakers,
                                fullText: panel.innerText
                            };
                        }''')
                        
                        if result_data:
                            detailed_results.append(result_data)
                    except Exception as e:
                        print(f"  [Lead Discovery] Scrape error: {e}")
                        pass

                collected["detailed_results"] = detailed_results

                # Fallback: if no structured data, get raw text
                if not detailed_results:
                    try:
                        right = await page.query_selector('.flex-1.overflow-y-auto')
                        if right:
                            collected["results_text"] = (await right.inner_text()).strip()
                    except:
                        pass

                # Leave browser open for demo
                print(f"  [Lead Discovery] Browser left open for demo.")

        except Exception as e:
            collected["errors"].append(f"Browser error: {str(e)}")
            print(f"  [Lead Discovery] ❌ Error: {e}")

        return collected

    def analyze(self, query: str) -> str:
        """Run a lead discovery analysis and return formatted results."""
        collected = self._run_async(self._async_analyze(query))
        return self._format_results(collected)

    def open_dashboard(self) -> str:
        """Open the dashboard in the default browser."""
        webbrowser.open(self.dashboard_url)
        return f"Opened Lead Discovery Dashboard at {self.dashboard_url}"

    def _format_results(self, collected: Dict[str, Any]) -> str:
        lines = [f"📊 Lead Discovery Results for: \"{collected['query']}\"\n"]

        if collected.get("errors"):
            lines.append("⚠️ Issues:")
            for err in collected["errors"]:
                lines.append(f"  - {err}")
            lines.append("")

        if collected.get("companies_found"):
            lines.append(f"🔎 Companies Found ({len(collected['companies_found'])}):")
            for c in collected["companies_found"]:
                lines.append(f"  • {c['name']}: {c.get('context', '')}")
            lines.append("")

        # Format structured results (with LinkedIn URLs)
        for result in collected.get("detailed_results", []):
            if not result:
                continue
                
            company = result.get("companyName", "Unknown")
            confidence = result.get("confidence", "?")
            summary = result.get("summary", "")
            
            lines.append(f"🏢 {company}")
            lines.append(f"   Confidence: {confidence}")
            if summary:
                lines.append(f"   {summary}")
            
            # Company details
            for detail in result.get("details", []):
                if detail.strip():
                    lines.append(f"   📌 {detail.strip()}")
            lines.append("")
            
            # Contacts with LinkedIn
            contacts = result.get("contacts", [])
            if contacts:
                lines.append("   👥 Contacts:")
                for c in contacts:
                    name = c.get("name", "?")
                    title = c.get("title", "")
                    email = c.get("email", "")
                    linkedin = c.get("linkedin", "")
                    
                    line = f"   • {name}"
                    if title:
                        line += f" — {title}"
                    if email and email != "-":
                        line += f" ✉️ {email}"
                    if linkedin:
                        line += f"\n     🔗 LinkedIn: {linkedin}"
                    lines.append(line)
                lines.append("")
            
            # Decision Makers
            dms = result.get("decisionMakers", [])
            if dms:
                lines.append("   🎯 Decision Makers:")
                for dm in dms:
                    name = dm.get("name", "?")
                    title = dm.get("title", "")
                    power = dm.get("power", "")
                    linkedin = dm.get("linkedin", "")
                    
                    line = f"   • {name}"
                    if title:
                        line += f" — {title}"
                    if power:
                        line += f" [{power}]"
                    if linkedin:
                        line += f"\n     🔗 LinkedIn: {linkedin}"
                    lines.append(line)
                lines.append("")

        # Fallback: raw text if no structured data
        if not collected.get("detailed_results") and collected.get("results_text"):
            lines.append("📋 Results:")
            lines.append(collected["results_text"][:3000])
            lines.append("")

        if collected.get("completed"):
            lines.append("✅ Pipeline complete!")

        lines.append(f"\n🌐 Dashboard: {collected.get('dashboard_url', self.dashboard_url)}")
        return "\n".join(lines)

    def close(self):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)
