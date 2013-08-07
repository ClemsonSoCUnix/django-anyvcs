#!/usr/bin/env python

import os
import shlex
import sys
import anyvcs.dispatch

if len(sys.argv) == 2:
  url = sys.argv[1]
  username = None
elif len(sys.argv) == 3:
  url, username = sys.argv[1:]
else:
  sys.stderr.write('Usage: %s <url> [<username>]\n' % sys.argv[0])
  sys.exit(1)

anyvcs.dispatch.ssh_dispatch(url, username)
