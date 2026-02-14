"""
WebMCP Client - Discovers and executes WebMCP tools on websites.

WebMCP (Web Model Context Protocol) lets websites expose structured tools
via navigator.modelContext so AI agents can interact with them through
defined APIs instead of fragile screen-scraping.

This module:
1. Navigates to a URL using Playwright (via BrowserPool)
2. Checks for navigator.modelContext.tools (native WebMCP)
3. Falls back to scanning for data-mcp-tool attributes (polyfill pattern)
4. Caches discovered tools per URL
5. Executes tools by calling the JS function on the page
"""

import json
from typing import Dict, List, Optional, Any

from core.browser_pool import BrowserPool


# JavaScript to discover WebMCP tools on a page
DISCOVER_TOOLS_JS = """
async () => {
    const tools = [];
    
    // Method 1: Check native navigator.modelContext API
    if (typeof navigator !== 'undefined' && navigator.modelContext) {
        try {
            const ctx = navigator.modelContext;
            
            // The WebMCP spec exposes tools as an array on modelContext
            if (ctx.tools && Array.isArray(ctx.tools)) {
                for (const tool of ctx.tools) {
                    tools.push({
                        name: tool.name || 'unnamed',
                        description: tool.description || '',
                        parameters: tool.inputSchema || tool.parameters || {},
                        source: 'navigator.modelContext'
                    });
                }
            }
            
            // Some implementations use a textContent/prompts pattern
            if (ctx.textContent && typeof ctx.textContent === 'function') {
                try {
                    const content = await ctx.textContent();
                    if (content) {
                        tools.push({
                            name: '__page_content',
                            description: 'Page text content exposed via WebMCP',
                            parameters: {},
                            source: 'navigator.modelContext.textContent',
                            content: typeof content === 'string' ? content.substring(0, 2000) : JSON.stringify(content).substring(0, 2000)
                        });
                    }
                } catch(e) {}
            }
        } catch(e) {
            console.error('WebMCP discovery error:', e);
        }
    }
    
    // Method 2: Check for MCP meta tags (declarative pattern)
    const mcpMeta = document.querySelectorAll('meta[name="mcp-tool"], meta[name="mcp-server"]');
    for (const meta of mcpMeta) {
        try {
            const content = JSON.parse(meta.getAttribute('content') || '{}');
            if (content.name) {
                tools.push({
                    name: content.name,
                    description: content.description || '',
                    parameters: content.inputSchema || content.parameters || {},
                    source: 'meta-tag'
                });
            }
        } catch(e) {}
    }
    
    // Method 3: Check for data-mcp-tool attributes (polyfill pattern)
    const mcpElements = document.querySelectorAll('[data-mcp-tool]');
    for (const el of mcpElements) {
        const toolName = el.getAttribute('data-mcp-tool');
        const toolDesc = el.getAttribute('data-mcp-description') || '';
        let toolParams = {};
        try {
            toolParams = JSON.parse(el.getAttribute('data-mcp-params') || '{}');
        } catch(e) {}
        
        tools.push({
            name: toolName,
            description: toolDesc,
            parameters: toolParams,
            source: 'data-attribute'
        });
    }
    
    // Method 4: Check for structured data (JSON-LD actions)
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of jsonLdScripts) {
        try {
            const data = JSON.parse(script.textContent);
            if (data.potentialAction) {
                const actions = Array.isArray(data.potentialAction) ? data.potentialAction : [data.potentialAction];
                for (const action of actions) {
                    if (action['@type'] && action.target) {
                        tools.push({
                            name: action['@type'],
                            description: action.description || action.name || action['@type'],
                            parameters: action.target || {},
                            source: 'json-ld'
                        });
                    }
                }
            }
        } catch(e) {}
    }
    
    return {
        hasWebMCP: tools.length > 0,
        toolCount: tools.length,
        tools: tools,
        url: window.location.href,
        title: document.title
    };
}
"""

# JavaScript template to execute a WebMCP tool
EXECUTE_TOOL_JS_TEMPLATE = """
async (toolName, args) => {{
    // Try navigator.modelContext first
    if (navigator.modelContext && navigator.modelContext.tools) {{
        const tool = navigator.modelContext.tools.find(t => t.name === toolName);
        if (tool && typeof tool.handler === 'function') {{
            try {{
                const result = await tool.handler(args);
                return {{ success: true, result: result, source: 'navigator.modelContext' }};
            }} catch(e) {{
                return {{ success: false, error: e.message, source: 'navigator.modelContext' }};
            }}
        }}
    }}
    
    // Try data-attribute elements
    const el = document.querySelector(`[data-mcp-tool="${{toolName}}"]`);
    if (el) {{
        // If it's a form, fill and submit
        if (el.tagName === 'FORM') {{
            for (const [key, value] of Object.entries(args)) {{
                const input = el.querySelector(`[name="${{key}}"]`);
                if (input) {{
                    input.value = value;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
            el.submit();
            return {{ success: true, result: 'Form submitted', source: 'data-attribute' }};
        }}
        
        // If it's a button or link, click it
        if (el.tagName === 'BUTTON' || el.tagName === 'A') {{
            el.click();
            return {{ success: true, result: 'Element clicked', source: 'data-attribute' }};
        }}
    }}
    
    return {{ success: false, error: `Tool '${{toolName}}' not found or not executable` }};
}}
"""


class WebMCPClient:
    """
    Client for discovering and executing WebMCP tools on websites.
    
    Uses Playwright via BrowserPool to navigate to pages, extract
    tool definitions from the WebMCP API, and execute them.
    """

    def __init__(self, headless: bool = True, timeout: int = 30):
        self.pool = BrowserPool(headless=headless, timeout=timeout)
        self._tool_cache: Dict[str, Dict] = {}  # url -> discovery result

    def discover_tools(self, url: str, force_refresh: bool = False) -> Dict:
        """
        Discover WebMCP tools available on a webpage.
        
        Args:
            url: The URL to scan for WebMCP tools.
            force_refresh: If True, bypass cache and re-scan.
            
        Returns:
            Dict with keys: hasWebMCP, toolCount, tools, url, title
        """
        # Check cache first
        if not force_refresh and url in self._tool_cache:
            cached = self._tool_cache[url]
            cached['fromCache'] = True
            return cached

        try:
            page = self.pool.get_page(url, force_new=force_refresh)
            result = self.pool.evaluate(page, DISCOVER_TOOLS_JS)
            
            if result and isinstance(result, dict):
                result['fromCache'] = False
                self._tool_cache[url] = result
                return result
            else:
                return {
                    'hasWebMCP': False,
                    'toolCount': 0,
                    'tools': [],
                    'url': url,
                    'title': '',
                    'fromCache': False,
                    'note': 'No WebMCP data returned from page'
                }

        except Exception as e:
            return {
                'hasWebMCP': False,
                'toolCount': 0,
                'tools': [],
                'url': url,
                'title': '',
                'fromCache': False,
                'error': str(e)
            }

    def execute_tool(self, url: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict:
        """
        Execute a WebMCP tool on a webpage.
        
        Args:
            url: The URL of the page containing the tool.
            tool_name: Name of the WebMCP tool to execute.
            arguments: Dict of arguments to pass to the tool.
            
        Returns:
            Dict with keys: success, result/error, source
        """
        if arguments is None:
            arguments = {}

        try:
            page = self.pool.get_page(url)
            
            # Build the execution script
            exec_js = f"""
            async () => {{
                const toolName = {json.dumps(tool_name)};
                const args = {json.dumps(arguments)};
                
                // Try navigator.modelContext first
                if (typeof navigator !== 'undefined' && navigator.modelContext && navigator.modelContext.tools) {{
                    const tool = navigator.modelContext.tools.find(t => t.name === toolName);
                    if (tool && typeof tool.handler === 'function') {{
                        try {{
                            const result = await tool.handler(args);
                            return {{ success: true, result: result, source: 'navigator.modelContext' }};
                        }} catch(e) {{
                            return {{ success: false, error: e.message, source: 'navigator.modelContext' }};
                        }}
                    }}
                }}
                
                // Try data-attribute elements
                const el = document.querySelector('[data-mcp-tool="' + toolName + '"]');
                if (el) {{
                    if (el.tagName === 'FORM') {{
                        for (const [key, value] of Object.entries(args)) {{
                            const input = el.querySelector('[name="' + key + '"]');
                            if (input) {{
                                input.value = value;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                        el.submit();
                        return {{ success: true, result: 'Form submitted', source: 'data-attribute' }};
                    }}
                    if (el.tagName === 'BUTTON' || el.tagName === 'A') {{
                        el.click();
                        return {{ success: true, result: 'Element clicked', source: 'data-attribute' }};
                    }}
                }}
                
                return {{ success: false, error: 'Tool "' + toolName + '" not found or not executable on this page' }};
            }}
            """
            
            result = self.pool.evaluate(page, exec_js)
            return result if result else {'success': False, 'error': 'No result returned'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_cached_tools(self) -> Dict[str, List]:
        """
        Get all cached tool discoveries.
        
        Returns:
            Dict mapping URLs to their discovered tools.
        """
        summary = {}
        for url, data in self._tool_cache.items():
            summary[url] = {
                'title': data.get('title', ''),
                'toolCount': data.get('toolCount', 0),
                'tools': [
                    {'name': t['name'], 'description': t['description']}
                    for t in data.get('tools', [])
                ]
            }
        return summary

    def clear_cache(self, url: str = None):
        """Clear tool cache for a specific URL or all URLs."""
        if url:
            self._tool_cache.pop(url, None)
            self.pool.close_page(url)
        else:
            self._tool_cache.clear()

    def close(self):
        """Shut down the browser pool and clean up resources."""
        self._tool_cache.clear()
        self.pool.close()
