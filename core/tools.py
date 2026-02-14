import subprocess
import os
from typing import Callable, Dict, Any, List
from utils.permissions import check_permission

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def register(self, func: Callable):
        """Decorator to register a tool."""
        self.tools[func.__name__] = func
        return func

    def get_tools(self) -> List[Callable]:
        return list(self.tools.values())
    
    def get_tool(self, name: str) -> Callable:
        return self.tools.get(name)

# Global registry instance
registry = ToolRegistry()

# Global memory store instance
_memory_store = None

def set_memory_store(store):
    global _memory_store
    _memory_store = store

@registry.register
def run_command(command: str) -> str:
    """
    Executes a shell command and returns the output.
    
    Args:
        command: The command to execute.
    """
    if not check_permission(command):
        return f"Permission Denied: Command '{command}' is not allowed."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return f"Output:\n{result.stdout}\nError:\n{result.stderr}"
    except Exception as e:
        return f"Error executing command: {e}"

@registry.register
def read_file(filepath: str) -> str:
    """
    Reads the content of a file.
    
    Args:
        filepath: The path to the file to read.
    """
    try:
        filepath = os.path.expanduser(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@registry.register
def write_file(filepath: str, content: str) -> str:
    """
    Writes content to a file. Overwrites if exists.
    
    Args:
        filepath: The path to the file to write.
        content: The content to write.
    """
    try:
        filepath = os.path.expanduser(filepath)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"

@registry.register
def web_search(query: str) -> str:
    """
    Performs a web search.
    
    Args:
        query: The search query.
    """
    # Placeholder for actual search implementation (e.g., using Google Search API or similar)
    return f"Mock search result for: {query}"

@registry.register
def save_memory(content: str) -> str:
    """
    Saves a memory to long-term storage.
    
    Args:
        content: The text content to save.
    """
    if _memory_store:
        try:
            _memory_store.add_memory(content)
            return "Memory saved successfully."
        except Exception as e:
            return f"Error saving memory: {e}"
    return "Memory store not configured."

@registry.register
def memory_search(query: str) -> str:
    """
    Searches long-term memory.
    
    Args:
        query: The search query.
    """
    if _memory_store:
        try:
            result = _memory_store.search_memory(query)
            return f"Found memory: {result}" if result else "No relevant memories found."
        except Exception as e:
            return f"Error searching memory: {e}"
    return "Memory store not configured."


# ==================== REMOTE CONTROL TOOLS ====================

@registry.register
def open_website(url: str) -> str:
    """
    Opens a URL in the default web browser on the laptop.
    Use this to open any website like YouTube, Google, GitHub, etc.
    
    Args:
        url: The full URL to open, e.g. https://www.youtube.com or https://google.com
    """
    import webbrowser
    try:
        webbrowser.open(url)
        return f"Successfully opened {url} in the browser."
    except Exception as e:
        return f"Error opening URL: {e}"


@registry.register
def open_application(app_name: str) -> str:
    """
    Opens an application on the Windows laptop by name.
    Common app names: notepad, calc, mspaint, explorer, cmd, powershell,
    spotify, discord, chrome, msedge, code (VS Code), excel, word, winword.
    
    Args:
        app_name: The name or path of the application to open.
    """
    try:
        if app_name.lower() == "whatsapp":
            # WhatsApp Desktop URI scheme
            import webbrowser
            webbrowser.open("whatsapp://")
            return "Successfully launched WhatsApp."
            
        subprocess.Popen(app_name, shell=True)
        return f"Successfully launched {app_name}."
    except Exception as e:
        return f"Error opening application: {e}"


@registry.register
def play_on_youtube(search_query: str) -> str:
    """
    Searches for and plays a video on YouTube.
    Use this when the user asks to play something on YouTube like a song, video, cartoon, movie, etc.
    
    Args:
        search_query: What to search for on YouTube, e.g. 'Ninja Hattori episode 1' or 'Night Changes One Direction'
    """
    import pywhatkit
    try:
        pywhatkit.playonyt(search_query)
        return f"Playing '{search_query}' on YouTube."
    except Exception as e:
        return f"Error playing on YouTube: {e}"


@registry.register
def media_control(action: str) -> str:
    """
    Controls media playback. Available actions:
    - 'play_pause': Play/Pause current media
    - 'next': Next track/video
    - 'previous': Previous track/video
    - 'volume_up': Increase volume
    - 'volume_down': Decrease volume
    - 'mute': Mute volume
    
    Args:
        action: The media action to perform.
    """
    import pyautogui
    import subprocess
    try:
        if action == "play_pause":
            pyautogui.press("playpause")
            return "Toggled Play/Pause."
        elif action == "next":
            pyautogui.press("nexttrack")
            return "Skipped to next track."
        elif action == "previous":
            pyautogui.press("prevtrack")
            return "Returned to previous track."
        elif action == "volume_up":
            # Use PowerShell for reliable volume control
            subprocess.run(
                'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"',
                shell=True, capture_output=True
            )
            return "Volume increased."
        elif action == "volume_down":
            subprocess.run(
                'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"',
                shell=True, capture_output=True
            )
            return "Volume decreased."
        elif action == "mute":
            subprocess.run(
                'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"',
                shell=True, capture_output=True
            )
            return "Volume muted/unmuted."
        else:
            return f"Unknown media action: {action}"
    except Exception as e:
        return f"Error controlling media: {e}"


@registry.register
def send_whatsapp_message(contact: str, message: str) -> str:
    """
    Sends a WhatsApp message using the WhatsApp Desktop app.
    Supports sending to phone numbers OR contact names.
    
    Args:
        contact: The phone number (with country code, e.g. '+91...') OR contact name (e.g. 'Mom', 'John').
        message: The text message content.
    """
    import webbrowser
    import pyautogui
    import time
    import urllib.parse
    
    try:
        # Check if contact is a phone number (mostly digits)
        is_phone = all(c.isdigit() or c == '+' for c in contact.replace(" ", "")) and len(contact) > 5
        
        if is_phone:
             # Use URI scheme for direct number
            encoded_message = urllib.parse.quote(message)
            url = f"whatsapp://send?phone={contact}&text={encoded_message}"
            webbrowser.open(url)
            time.sleep(2) # Wait for app
            pyautogui.press('enter')
            return f"Opened WhatsApp chat with {contact} and sent message: '{message}'"
        
        else:
            # Use UI Automation for Contact Name
            # 1. Open WhatsApp
            webbrowser.open("whatsapp://")
            time.sleep(1) # Wait for app focus
            
            # 2. Search for contact (Ctrl + Alt + N is New Chat, or just Ctrl + N usually)
            # Try Ctrl + N for new chat
            pyautogui.hotkey('ctrl', 'n')
            time.sleep(0.5)
            
            # 3. Type contact name
            pyautogui.write(contact)
            time.sleep(1) # Wait for search results
            
            # 4. Select contact (Enter)
            pyautogui.press('enter')
            time.sleep(0.5)
            
            # 5. Type message
            pyautogui.write(message)
            time.sleep(0.5)
            
            # 6. Send
            pyautogui.press('enter')
            
            return f"Opened WhatsApp, searched for '{contact}', and sent message: '{message}'"
            
    except Exception as e:
        return f"Error sending WhatsApp message: {e}"


@registry.register
def play_on_spotify(search_query: str) -> str:
    """
    Searches for and plays a song or artist on the Spotify desktop app.
    The Spotify app must be installed on the laptop.
    
    Args:
        search_query: The song, artist, or album to search for on Spotify, e.g. 'Night Changes' or 'One Direction'
    """
    import urllib.parse
    try:
        encoded = urllib.parse.quote(search_query)
        # Open Spotify search URI - this opens the Spotify app directly
        spotify_uri = f"spotify:search:{encoded}"
        os.startfile(spotify_uri)
        return f"Opened Spotify search for '{search_query}'."
    except Exception as e:
        # Fallback: open Spotify web search
        try:
            import webbrowser
            url = f"https://open.spotify.com/search/{urllib.parse.quote(search_query)}"
            webbrowser.open(url)
            return f"Opened Spotify web search for '{search_query}' (desktop app may not be available)."
        except Exception as e2:
            return f"Error opening Spotify: {e2}"


@registry.register
def system_control(action: str) -> str:
    """
    Controls the Windows laptop system. Available actions:
    - 'volume_up': Increase volume
    - 'volume_down': Decrease volume  
    - 'volume_mute': Mute/unmute volume
    - 'screenshot': Take a screenshot and save it
    - 'lock': Lock the screen
    - 'shutdown': Shutdown the computer (asks for confirmation)
    - 'restart': Restart the computer (asks for confirmation)
    - 'sleep': Put computer to sleep
    - 'brightness_up': Increase brightness
    - 'brightness_down': Decrease brightness
    
    Args:
        action: The system action to perform.
    """
    try:
        if action == "volume_up":
            # Use PowerShell to press volume up key
            subprocess.run(
                'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"',
                shell=True, capture_output=True
            )
            return "Volume increased."
            
        elif action == "volume_down":
            subprocess.run(
                'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"',
                shell=True, capture_output=True
            )
            return "Volume decreased."
            
        elif action == "volume_mute":
            subprocess.run(
                'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"',
                shell=True, capture_output=True
            )
            return "Volume muted/unmuted."
            
        elif action == "screenshot":
            # Use PowerShell to take a screenshot
            screenshot_path = os.path.join(os.path.expanduser("~"), "Desktop", "screenshot.png")
            subprocess.run(
                f'powershell -c "Add-Type -AssemblyName System.Windows.Forms; '
                f'[System.Windows.Forms.Screen]::PrimaryScreen | ForEach-Object {{ '
                f'$bitmap = New-Object System.Drawing.Bitmap($_.Bounds.Width, $_.Bounds.Height); '
                f'$graphics = [System.Drawing.Graphics]::FromImage($bitmap); '
                f'$graphics.CopyFromScreen($_.Bounds.Location, [System.Drawing.Point]::Empty, $_.Bounds.Size); '
                f'$bitmap.Save(\'{screenshot_path}\'); }}"',
                shell=True, capture_output=True
            )
            return f"Screenshot saved to {screenshot_path}"
            
        elif action == "lock":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Screen locked."
            
        elif action == "shutdown":
            subprocess.run("shutdown /s /t 60", shell=True)
            return "Computer will shutdown in 60 seconds. Run 'shutdown /a' to cancel."
            
        elif action == "restart":
            subprocess.run("shutdown /r /t 60", shell=True)
            return "Computer will restart in 60 seconds. Run 'shutdown /a' to cancel."
            
        elif action == "sleep":
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "Computer going to sleep."
            
        elif action == "brightness_up":
            subprocess.run(
                'powershell -c "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [Math]::Min(100, (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness + 10))"',
                shell=True, capture_output=True
            )
            return "Brightness increased."
            
        elif action == "brightness_down":
            subprocess.run(
                'powershell -c "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [Math]::Max(0, (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness - 10))"',
                shell=True, capture_output=True
            )
            return "Brightness decreased."
            
        else:
            return f"Unknown action: {action}. Available: volume_up, volume_down, volume_mute, screenshot, lock, shutdown, restart, sleep, brightness_up, brightness_down"
            
    except Exception as e:
        return f"Error performing system action: {e}"


@registry.register
def get_system_info(info_type: str) -> str:
    """
    Gets system information from the Windows laptop. Available info types:
    - 'battery': Battery percentage and charging status
    - 'ip': IP address of the laptop
    - 'disk': Disk space usage
    - 'processes': List of running processes
    - 'wifi': Current WiFi network name
    - 'uptime': How long the computer has been running
    
    Args:
        info_type: The type of system info to retrieve.
    """
    try:
        if info_type == "battery":
            result = subprocess.run(
                'powershell -c "Get-WmiObject Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus | Format-List"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Battery info:\n{result.stdout}" if result.stdout.strip() else "No battery detected (desktop PC)."
            
        elif info_type == "ip":
            result = subprocess.run(
                'powershell -c "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike \'*Loopback*\'}).IPAddress"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"IP Addresses:\n{result.stdout}"
            
        elif info_type == "disk":
            result = subprocess.run(
                'powershell -c "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{n=\'Used(GB)\';e={[math]::Round($_.Used/1GB,2)}}, @{n=\'Free(GB)\';e={[math]::Round($_.Free/1GB,2)}} | Format-Table"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Disk usage:\n{result.stdout}"
            
        elif info_type == "processes":
            result = subprocess.run(
                'powershell -c "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, CPU, WorkingSet | Format-Table"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Top processes:\n{result.stdout}"
            
        elif info_type == "wifi":
            result = subprocess.run(
                'netsh wlan show interfaces | findstr /R "SSID Signal"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"WiFi info:\n{result.stdout}" if result.stdout.strip() else "No WiFi connection found."
            
        elif info_type == "uptime":
            result = subprocess.run(
                'powershell -c "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | Select-Object Days, Hours, Minutes | Format-List"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"System uptime:\n{result.stdout}"
            
        else:
            return f"Unknown info type: {info_type}. Available: battery, ip, disk, processes, wifi, uptime"
            
    except Exception as e:
        return f"Error getting system info: {e}"


# ==================== WEBMCP TOOLS ====================

# Global WebMCP client instance (injected from main.py)
_webmcp_client = None

def set_webmcp_client(client):
    global _webmcp_client
    _webmcp_client = client


@registry.register
def webmcp_discover_tools(url: str) -> str:
    """
    Discovers WebMCP tools available on a webpage. WebMCP lets websites expose
    structured actions (like booking, searching, form submission) that AI agents
    can call directly instead of guessing the UI.

    Use this when the user asks you to interact with a specific website, 
    or to find out what actions a website supports.

    Args:
        url: The full URL of the webpage to scan for WebMCP tools, e.g. 'https://example.com'
    """
    if not _webmcp_client:
        return "WebMCP is not enabled. Set WEBMCP_ENABLED=true in .env and install playwright."
    
    try:
        import json
        result = _webmcp_client.discover_tools(url)
        
        if result.get('error'):
            return f"Error discovering tools on {url}: {result['error']}"
        
        if not result.get('hasWebMCP'):
            return (
                f"No WebMCP tools found on '{result.get('title', url)}'.\n"
                f"This website hasn't implemented WebMCP yet. "
                f"You can still interact with it using open_website() or run_command()."
            )
        
        # Format tools for the agent
        tools_info = []
        for tool in result.get('tools', []):
            info = f"- {tool['name']}: {tool['description']}"
            if tool.get('parameters'):
                info += f"\n  Parameters: {json.dumps(tool['parameters'], indent=2)}"
            tools_info.append(info)
        
        return (
            f"Found {result['toolCount']} WebMCP tool(s) on '{result.get('title', url)}':\n\n"
            + "\n".join(tools_info)
            + "\n\nUse webmcp_execute_tool() to call any of these tools."
        )
    except Exception as e:
        return f"Error discovering WebMCP tools: {e}"


@registry.register
def webmcp_execute_tool(url: str, tool_name: str, arguments: str = "{}") -> str:
    """
    Executes a WebMCP tool on a webpage. First use webmcp_discover_tools() to find
    available tools, then call this to execute one.

    Args:
        url: The URL of the webpage containing the tool.
        tool_name: The name of the WebMCP tool to execute (from discover results).
        arguments: A JSON string of arguments to pass, e.g. '{"query": "flights to NYC"}'
    """
    if not _webmcp_client:
        return "WebMCP is not enabled. Set WEBMCP_ENABLED=true in .env and install playwright."
    
    try:
        import json
        args_dict = json.loads(arguments) if isinstance(arguments, str) else arguments
        
        result = _webmcp_client.execute_tool(url, tool_name, args_dict)
        
        if result.get('success'):
            return (
                f"Successfully executed WebMCP tool '{tool_name}' on {url}.\n"
                f"Source: {result.get('source', 'unknown')}\n"
                f"Result: {json.dumps(result.get('result', ''), indent=2)}"
            )
        else:
            return (
                f"Failed to execute WebMCP tool '{tool_name}' on {url}.\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
    except json.JSONDecodeError:
        return f"Invalid JSON in arguments: {arguments}. Must be a valid JSON string."
    except Exception as e:
        return f"Error executing WebMCP tool: {e}"


@registry.register
def webmcp_list_cached_tools() -> str:
    """
    Lists all previously discovered WebMCP tools from cache.
    Use this to see what websites and tools have already been discovered
    without needing to re-scan pages.
    """
    if not _webmcp_client:
        return "WebMCP is not enabled."
    
    try:
        import json
        cached = _webmcp_client.get_cached_tools()
        
        if not cached:
            return "No WebMCP tools have been discovered yet. Use webmcp_discover_tools(url) to scan a website."
        
        lines = ["Previously discovered WebMCP tools:\n"]
        for url, data in cached.items():
            lines.append(f"📌 {data.get('title', url)} ({url})")
            lines.append(f"   Tools ({data['toolCount']}):")
            for tool in data.get('tools', []):
                lines.append(f"   - {tool['name']}: {tool['description']}")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing cached tools: {e}"


# ==================== LEAD DISCOVERY TOOLS ====================

# Global Lead Discovery client instance (injected from main.py)
_lead_discovery_client = None

def set_lead_discovery_client(client):
    global _lead_discovery_client
    _lead_discovery_client = client


@registry.register
def lead_discovery_search(query: str) -> str:
    """
    Searches for B2B leads using the Lead Discovery Agent. Opens the dashboard
    in a visible browser, runs the full pipeline, and returns results.
    
    Pipeline: Discovery → Structure → Roles → Enrichment → Verification.
    
    Use this for queries like:
    - 'startups in Bangalore'
    - 'AI companies in San Francisco'
    - 'Google' (single company analysis)
    - 'find product managers at Microsoft'
    
    WARNING: This can take 2-5 minutes as it runs a deep analysis pipeline.
    The dashboard will open visibly on the laptop for demo.
    
    Args:
        query: The search query - company name, industry search, or role-based search.
    """
    if not _lead_discovery_client:
        return "Lead Discovery is not enabled. Set LEAD_DISCOVERY_ENABLED=true in .env and ensure the server is running."
    
    try:
        print(f"[Lead Discovery] Starting pipeline for: {query}")
        print(f"[Lead Discovery] Dashboard: {_lead_discovery_client.dashboard_url}")
        print(f"[Lead Discovery] This may take several minutes...")
        
        # Opens visible browser, types query, waits for results, scrapes them
        result = _lead_discovery_client.analyze(query)
        
        # Add instruction so the model sends this to the user instead of calling more tools
        return (
            "[INSTRUCTION: Send the following lead discovery results directly to the user. "
            "Do NOT call any more tools. Just format and present these results nicely.]\n\n"
            + result
        )
        
    except Exception as e:
        return f"Error running lead discovery: {e}"


@registry.register
def lead_discovery_open_dashboard() -> str:
    """
    Opens the B2B Lead Discovery web dashboard in the browser for visual demo.
    Use this when the user wants to see the Lead Discovery UI or interact with it visually.
    """
    if _lead_discovery_client:
        return _lead_discovery_client.open_dashboard()
    
    import webbrowser
    webbrowser.open("https://agent-three-eta.vercel.app/")
    return "Opened Lead Discovery Dashboard at https://agent-three-eta.vercel.app/"


