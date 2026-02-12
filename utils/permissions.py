import re

class PermissionSystem:
    def __init__(self, mode: str = "ask"):
        self.mode = mode  # ask, allow, deny
        # Simple dangerous patterns
        self.dangerous_patterns = [
            r"rm\s+-rf",
            r"mkfs",
            r"dd\s+if=",
            r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", # fork bomb
            r">\s*/dev/sd",
            r"Format-Volume", # Windows specific
            r"Remove-Item.*-Recurse", # Windows specific equivalent to rm -rf mostly
        ]

    def is_safe(self, command: str) -> bool:
        if self.mode == "deny":
            return False
        if self.mode == "allow":
            return True
        
        # Check against dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                print(f"Blocked dangerous command: {command}")
                return False
        
        return True

    def request_permission(self, command: str) -> bool:
        if self.mode == "allow":
            return True
        if self.mode == "deny":
            return False
            
        if not self.is_safe(command):
            print(f"WARNING: Command '{command}' detected as potentially dangerous.")
            
        # In a real CLI/interactive mode we would ask input()
        # But since we are running potentially headless or via Telegram, 
        # we need a way to route this permission request.
        # For MVP, we'll just log and maybe default to SAFE ONLY in 'ask' mode without interactive prompt.
        # Or actually rely on the user to have configured 'allow' if they want autonomy.
        
        # PROVISIONAL: For this agentic implementation, we will log and return True IF it passed basic safety checks.
        # If it failed safety checks, we return False.
        return self.is_safe(command)

# Global API
_permission_system = PermissionSystem()

def check_permission(command: str) -> bool:
    return _permission_system.request_permission(command)
