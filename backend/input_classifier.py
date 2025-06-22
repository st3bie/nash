import shlex

def is_shell_command(text):
    try:
        parts = shlex.split(text)
        return len(parts) > 0 and parts[0] in KNOWN_COMMANDS
    except Exception:
        return False

KNOWN_COMMANDS = {
    "ls", "cd", "git", "cat", "grep", "make", "python", "rm", "cp", "mv", "docker",
    "npm", "yarn", "curl", "wget", "echo", "touch", "mkdir", "find", "pwd"
}
