import pty, os, time, sys
m, s = pty.openpty()
open(sys.argv[1], "w").write(os.ttyname(s))
while True:
    try:
        os.read(m, 4096)   # drain output so writes never block
    except OSError:
        time.sleep(0.2)
