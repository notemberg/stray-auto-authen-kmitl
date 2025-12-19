import sys

cmd = sys.argv[1] if len(sys.argv) > 1 else None

if not cmd:
    print("Usage: authctl reconnect | logout")
    sys.exit(0)

with open("command.txt", "w") as f:
    f.write(cmd)
