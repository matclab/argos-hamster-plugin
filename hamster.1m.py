#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
import os
import sys
import csv
import itertools
import functools
from subprocess import Popen, PIPE
from datetime import date, timedelta, datetime
from dataclasses import dataclass
from collections import Counter
from xdg.BaseDirectory import xdg_data_home
from shutil import which

from enum import Enum, auto
class Version(Enum):
    ONE = auto()
    TWO = auto()


##### Customization
# Shall we use an icon instead of the current activity in the
USE_ICON=False

# Choose your hamster version
# ⚠ hamster 1.04 doesn't leave when the window to add new activity
#   is closed and as such it will leave many backround processes.
HAMSTER_VERSION  = Version.TWO
# HAMSTER_VERSION : Version.ONE

# How many days to look back in the past in order to get past activities
DAYS = 14
# Whether to rank recent activities by age and frequency
AGE_FREQUENCY_RANKING = False
# Whether to include the description for recent activities
USE_DESCRIPTION = True

MENU_COLOR = "#919191"
MENU_SIZE = 10
# scale factor for your DPI
SCALE = '1'

###### End of customization

scale = float(SCALE)
iconHeight = str(int(24 * scale))
iconWidth = str(int(30 * scale))
MENU_WIDTH =  18 # monospace chars

if which("inotifywait"):
# command to wait for change to hamster.db then touch this script
    dbpath = os.path.join(xdg_data_home, 'hamster-applet', 'hamster.db')
    script = '~/.config/argos/' + os.path.basename(sys.argv[0])
    touchScript = f'; inotifywait "{dbpath}" -e modify ; touch {script}'
else:
    touchScript = ""


if HAMSTER_VERSION is Version.TWO:
    ADD_ACTIVITY_CMD = f"hamster add  {touchScript}" # For hamster 2+
else:
    ADD_ACTIVITY_CMD = f"hamster {touchScript}" # For hamster 1.04


def hamster(cmd, strip=True):
    proc = Popen(f"LC_ALL=C hamster {cmd}", stdout=PIPE, shell=True)
    res, _ = proc.communicate()
    proc.wait()
    res = res.decode('utf8')
    if strip:
        return res.strip()
    else:
        return res

def dec2sex(hd:int) -> str:
    m, s = divmod(hd*3600, 60)
    h, m = divmod(m, 60)
    h = int(h)
    m = int(m)
    if m:
        return f"{h}h{m}m"
    else:
        return f"{h}h"


def recent_activities():
    """ Return a sequence of (activity, category, description, tags)
    corresponding to the last uniques activities seen DAYS before"""
    today = date.today()
    now = today.isoformat()
    before = (date.today() - timedelta(days=DAYS)).isoformat()
    act = hamster(f"export tsv {before} {now}", strip=False).split("\n")[1:-2]
    rank = Counter()
    for activity, start, end, duration, category, description, tags \
        in csv.reader(act, delimiter="\t"):
        desctxt = ", " + description if description and USE_DESCRIPTION else ""
        fact = f"{activity}@{category}{desctxt} "
        tagtxt = " #%s" % " #".join(tags.split(', ')) if tags else ""
        # Build fact txt without spurious comma
        fact =  f"{fact}{tagtxt}" if desctxt else ','.join(filter(None,(fact, tagtxt)))
        if AGE_FREQUENCY_RANKING:
            # same rough age-frequency ranking used in hamster
            start = datetime.strptime(start[:10], "%Y-%m-%d").date()
            rank[fact] += DAYS - int((today - start).days)
        else:
            rank[fact] = 1
    if AGE_FREQUENCY_RANKING:
        return [k for (v, k) in reversed(sorted(((v, k) for (k, v) in rank.items())))]
    else:
        return list(sorted(rank))

@dataclass
class Hamster():
    current_full: str = ''
    current_activity: str = ''
    active: bool = False

    def task_bar(self):
        self.current_full = hamster("current")
        self.current_activity = self.current_full
        if self.current_activity != "No activity":
            a = " ".join(self.current_full.split('@')[0].split()[2:]) # activity
            self.current_activity = a + " " + self.current_full[-5:]  # time
            self.active = True
        if USE_ICON:
            print(f" |image={ICON} imageHeight={iconHeight} imageWidth={iconWidth}")
        else:
            print(self.current_activity)
        print("---")


    def header(self):
        thisfile = os.path.abspath(__file__)
        print(f"Current activity | size={MENU_SIZE} | color={MENU_COLOR}")
        begin = "<span font_family='monospace'>"
        end = f"<b>+</b></span> | terminal=false refresh=true " \
                 f"bash='{ADD_ACTIVITY_CMD}'"
        if self.active:
            txt = " ".join(self.current_full.split(',')[0].split()[2:])
        else:
            txt = self.current_activity
        spaces = " " * (max(1, MENU_WIDTH-len(txt)))
        print(f"{begin}{txt}{spaces}{end}")
        if self.active:
            print("Stop Tracking | terminal=false refresh=true bash='hamster stop'")

    def recent(self):
        print(f"Recent activities | size={MENU_SIZE} | color={MENU_COLOR}")
        for fact in recent_activities():
            print(f"-- {fact} | terminal=false refresh=true "
                  f"bash=\'hamster start \"{fact}\"\'")

    def footer(self ):
        print("---")
        print("Show Overview | terminal=false"
              " refresh=true bash='hamster overview {touchScript}'")
        if HAMSTER_VERSION == Version.ONE:
            fulltotal = hamster("list").split("\n")[-1]
            total = sum(map(
                lambda x: float(x.split(':')[1][:-1]),
                fulltotal.split(',')))
            total = dec2sex(total)
        else:
            actlist = hamster("list").split("\n")[2:]
            total = actlist[-1].split(':')[1][:-2]\
                    .replace(" 0m","").replace(' ','') or "0h"
            # find end of array
            for i,l in enumerate(actlist):
                if l.startswith("------"):
                    break
            # Remove "in" de "min", remove empty hours and minutes, and spaces
            fulltotal = ",".join(map(lambda x: x[:-2]
                                       .replace(" 0h 0m","0h")\
                                       .replace(" 0m","")\
                                       .replace(" 0h","")\
                                       .replace(" ",""),
                                            actlist[i+1:-1]))

        print(f"<b>total</b>: {total} "
              + (f"<small>({fulltotal})</small>" if fulltotal else "")
              + f" | color={MENU_COLOR}")


    def generate(self):
        self.task_bar()
        self.header()
        self.recent()
        self.footer()



# Hamster SVG icon
ICON="PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPCEtLSBDcmVhdGVkIHdpdGggSW5rc2NhcGUgKGh0dHA6Ly93d3cuaW5rc2NhcGUub3JnLykgLS0+CjxzdmcgaWQ9InN2ZzIiIHdpZHRoPSI0OCIgaGVpZ2h0PSI0OCIgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIj4KIDxkZWZzIGlkPSJkZWZzNCI+CiAgPGxpbmVhckdyYWRpZW50IGlkPSJsaW5lYXJHcmFkaWVudDY2MzAiPgogICA8c3RvcCBpZD0ic3RvcDY2MzIiIHN0b3AtY29sb3I9IiNhMmE1OWUiIG9mZnNldD0iMCIvPgogICA8c3RvcCBpZD0ic3RvcDY2MzQiIHN0b3AtY29sb3I9IiNjYWNjYzciIG9mZnNldD0iMSIvPgogIDwvbGluZWFyR3JhZGllbnQ+CiAgPGxpbmVhckdyYWRpZW50IGlkPSJsaW5lYXJHcmFkaWVudDYxNTQiIHgxPSIxOC4wNjIiIHgyPSIxOC41IiB5MT0iNy44NzUiIHkyPSIxMC4zNzUiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoMSwwLDAsLTEsMiw0NCkiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgPHN0b3AgaWQ9InN0b3A2MTQ0IiBzdG9wLWNvbG9yPSIjM2I3NGJkIiBvZmZzZXQ9IjAiLz4KICAgPHN0b3AgaWQ9InN0b3A2MTQ2IiBzdG9wLWNvbG9yPSIjMmY1ODk0IiBvZmZzZXQ9IjEiLz4KICA8L2xpbmVhckdyYWRpZW50PgogIDxmaWx0ZXIgaWQ9ImZpbHRlcjYzMzkiIHg9Ii0uMTA3ODQiIHk9Ii0uNjU3MTQiIHdpZHRoPSIxLjIxNTciIGhlaWdodD0iMi4zMTQzIj4KICAgPGZlR2F1c3NpYW5CbHVyIGlkPSJmZUdhdXNzaWFuQmx1cjYzNDEiIHN0ZERldmlhdGlvbj0iMS4wOTUyMzQ1Ii8+CiAgPC9maWx0ZXI+CiAgPGxpbmVhckdyYWRpZW50IGlkPSJsaW5lYXJHcmFkaWVudDY0OTMiIHgxPSI0OC4wNDQiIHgyPSI1OC4wMDgiIHkxPSIxOS44ODgiIHkyPSI0NS42MzIiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoLjk1Mjk4IDAgMCAuODM4NTEgLTI4LjY4OCAzLjU0OSkiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgPHN0b3AgaWQ9InN0b3A1OTgxIiBzdG9wLWNvbG9yPSIjOTFiNWRhIiBvZmZzZXQ9IjAiLz4KICAgPHN0b3AgaWQ9InN0b3A1OTgzIiBzdG9wLWNvbG9yPSIjNTM4NWJkIiBvZmZzZXQ9IjEiLz4KICA8L2xpbmVhckdyYWRpZW50PgogIDxsaW5lYXJHcmFkaWVudCBpZD0ibGluZWFyR3JhZGllbnQ2NDk1IiB4MT0iNTIuMzIiIHgyPSI2MS4wNzciIHkxPSIxMS43MjkiIHkyPSI0My40NzEiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoLjk1Mjk4IDAgMCAuODM4NTMgLTI2Ljc4MiAzLjU0ODIpIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CiAgIDxzdG9wIGlkPSJzdG9wNjExNCIgc3RvcC1jb2xvcj0iIzNjNzViZSIgb2Zmc2V0PSIwIi8+CiAgIDxzdG9wIGlkPSJzdG9wNjExNiIgc3RvcC1jb2xvcj0iIzM0NjVhNCIgb2Zmc2V0PSIxIi8+CiAgPC9saW5lYXJHcmFkaWVudD4KICA8bGluZWFyR3JhZGllbnQgaWQ9ImxpbmVhckdyYWRpZW50NjUxNSIgeDE9IjE5LjI1IiB4Mj0iMTkuMTYyIiB5MT0iNDUuNjI1IiB5Mj0iMzciIGdyYWRpZW50VHJhbnNmb3JtPSJ0cmFuc2xhdGUoMiwtMikiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgPHN0b3AgaWQ9InN0b3A2MzQ5IiBzdG9wLWNvbG9yPSIjYTlhY2E0IiBvZmZzZXQ9IjAiLz4KICAgPHN0b3AgaWQ9InN0b3A2MzUxIiBzdG9wLWNvbG9yPSIjZTJlM2UxIiBvZmZzZXQ9IjEiLz4KICA8L2xpbmVhckdyYWRpZW50PgogIDxyYWRpYWxHcmFkaWVudCBpZD0icmFkaWFsR3JhZGllbnQ2NTgyIiBjeD0iMjIuMTI1IiBjeT0iMjIuMzc1IiByPSIxNy45OTYiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoLjAxMzg5MiAuOTM3NjkgLTEuMDAwMiAuMDE0ODIgNDYuMTk3IC0uNzAyOSkiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgPHN0b3AgaWQ9InN0b3A2NTkyIiBzdG9wLWNvbG9yPSIjMjA0YTg3IiBvZmZzZXQ9IjAiLz4KICAgPHN0b3AgaWQ9InN0b3A2NTk0IiBzdG9wLWNvbG9yPSIjMzQ2NWE0IiBvZmZzZXQ9IjAiLz4KICAgPHN0b3AgaWQ9InN0b3A2NTk2IiBzdG9wLWNvbG9yPSIjNDM3M2FlIiBvZmZzZXQ9Ii40NDkwOSIvPgogICA8c3RvcCBpZD0ic3RvcDY1OTgiIHN0b3AtY29sb3I9IiMzNDY1YTQiIG9mZnNldD0iLjU5NTMxIi8+CiAgIDxzdG9wIGlkPSJzdG9wNjYwMCIgc3RvcC1jb2xvcj0iIzcyOWZjZiIgb2Zmc2V0PSIxIi8+CiAgPC9yYWRpYWxHcmFkaWVudD4KICA8bGluZWFyR3JhZGllbnQgaWQ9ImxpbmVhckdyYWRpZW50NjY4OCIgeDE9IjIxLjk3MiIgeDI9IjIxLjIyMyIgeTE9IjM5LjUiIHkyPSIyOS4yNjciIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoMS4wMDE4IDAgMCAuOTUwODkgMS45OTIgLTEuMDQwNikiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgPHN0b3AgaWQ9InN0b3A2NDQ5IiBzdG9wLWNvbG9yPSIjYThhYmE0IiBvZmZzZXQ9IjAiLz4KICAgPHN0b3AgaWQ9InN0b3A2NDUxIiBzdG9wLWNvbG9yPSIjY2NjZGM5IiBvZmZzZXQ9IjEiLz4KICA8L2xpbmVhckdyYWRpZW50PgogIDxsaW5lYXJHcmFkaWVudCBpZD0ibGluZWFyR3JhZGllbnQ2NjkwIiB4MT0iMjAuNjIyIiB4Mj0iMjAuODc1IiB5MT0iMjYuODkxIiB5Mj0iMzguMDA0IiBncmFkaWVudFRyYW5zZm9ybT0ibWF0cml4KDEuMDAxOCAwIDAgLjk5ODM2IDEuOTkyIC0xLjk2NjIpIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CiAgIDxzdG9wIGlkPSJzdG9wNjYwNiIgc3RvcC1jb2xvcj0iIzc2Nzk3NCIgb2Zmc2V0PSIwIi8+CiAgIDxzdG9wIGlkPSJzdG9wNjYwOCIgc3RvcC1jb2xvcj0iIzU1NTc1MyIgb2Zmc2V0PSIxIi8+CiAgPC9saW5lYXJHcmFkaWVudD4KICA8bGluZWFyR3JhZGllbnQgaWQ9ImxpbmVhckdyYWRpZW50NjY5MiIgeDE9IjM3LjgxMiIgeDI9IjM3Ljk1NiIgeTE9IjM5LjAzMSIgeTI9IjQwIiBncmFkaWVudFRyYW5zZm9ybT0idHJhbnNsYXRlKDIsLTIpIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSIgeGxpbms6aHJlZj0iI2xpbmVhckdyYWRpZW50NjYzMCIvPgogIDxsaW5lYXJHcmFkaWVudCBpZD0ibGluZWFyR3JhZGllbnQ2Njk2IiB4MT0iMzcuODEyIiB4Mj0iMzcuOTU2IiB5MT0iMzkuMDMxIiB5Mj0iNDAiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoLTEgMCAwIDEgNDYuMTQgLTIpIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSIgeGxpbms6aHJlZj0iI2xpbmVhckdyYWRpZW50NjYzMCIvPgogIDxmaWx0ZXIgaWQ9ImZpbHRlcjcyMjAiIHg9Ii0uMDgyMTQyIiB5PSItLjYyOTc2IiB3aWR0aD0iMS4xNjQzIiBoZWlnaHQ9IjIuMjU5NSI+CiAgIDxmZUdhdXNzaWFuQmx1ciBpZD0iZmVHYXVzc2lhbkJsdXI3MjIyIiBzdGREZXZpYXRpb249IjEuNTc0Mzk0NSIvPgogIDwvZmlsdGVyPgogPC9kZWZzPgogPGcgaWQ9ImxheWVyMSI+CiAgPHJlY3QgaWQ9InJlY3Q3MjEwIiB0cmFuc2Zvcm09Im1hdHJpeCgxIDAgMCAuODMzMzMgLTExMCAtNzAuNjY3KSIgeD0iMTExIiB5PSIxMzQiIHdpZHRoPSI0NiIgaGVpZ2h0PSI2IiByeD0iMi44NzUiIHJ5PSIzLjQ1IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGZpbHRlcj0idXJsKCNmaWx0ZXI3MjIwKSIgb3BhY2l0eT0iLjMwNTI2Ii8+CiAgPHBhdGggaWQ9InBhdGg2MjIzIiBkPSJtNDMuNSAzNi42MjUgMyA1Ljc1YzAgMS4xNzcyLTAuOTQ3NzUgMi4xMjUtMi4xMjUgMi4xMjVoLTQwLjc1Yy0xLjE3NzIgMC0yLjEyNS0wLjk0Nzc1LTIuMTI1LTIuMTI1bDMtNS43NXoiIGZpbGw9IiM4ODhhODUiIGZpbGwtcnVsZT0iZXZlbm9kZCIgc3Ryb2tlPSIjNTU1NzUzIi8+CiAgPHBhdGggaWQ9InJlY3Q2MjIwIiBkPSJtNi42MjUgMzUuNWgzNC43NWMxLjE3NzIgMCAxLjgxMjUtMC4wNTIyNSAyLjEyNSAxLjEyNWwzIDMuNzVjMCAxLjE3NzItMC45NDc3NSAyLjEyNS0yLjEyNSAyLjEyNWgtNDAuNzVjLTEuMTc3MiAwLTIuMTI1LTAuOTQ3NzUtMi4xMjUtMi4xMjVsMy0zLjc1YzAuNTYyNS0xLjExNDggMC45NDc3NS0xLjEyNSAyLjEyNS0xLjEyNXoiIGZpbGw9InVybCgjbGluZWFyR3JhZGllbnQ2NTE1KSIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9IiM1NTU3NTMiLz4KICA8cGF0aCBpZD0icGF0aDYxOTYiIGQ9Im0yNC4wMzEgMTguNTMxYy0wLjkzNTk2LTAuMDM1ODMtMS40NDAxIDAuOTM1OTYtMS40NDAxIDAuOTM1OTZsLTE2LjA5MSAxOC4wMDJoMi45NzQxbDEzLjQ5My0xNS4yNTZzMC4zOTMyOC0wLjc0NDg0IDEuMDY0NC0wLjcxNzU3YzAuNzAyODIgMC4wMjg1NyAxLjAzMzEgMC43MTc1NyAxLjAzMzEgMC43MTc1N2wxMy40NjIgMTUuMjg3aDIuOTc0MWwtMTYuMDI5LTE4LjAzM3MtMC40NTk5Mi0wLjg5ODQ1LTEuNDQwMS0wLjkzNTk2eiIgZmlsbD0idXJsKCNsaW5lYXJHcmFkaWVudDY2ODgpIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiIHN0cm9rZT0idXJsKCNsaW5lYXJHcmFkaWVudDY2OTApIiBzdHJva2Utd2lkdGg9IjFweCIvPgogIDxlbGxpcHNlIGlkPSJwYXRoNjI2MSIgdHJhbnNmb3JtPSJtYXRyaXgoMS4zMTI4IDAgMCAxIC00LjQ3MTggLTIuNSkiIGN4PSIyMS42ODgiIGN5PSI0MS41IiByeD0iMTIuMTg4IiByeT0iMiIgZmlsbC1ydWxlPSJldmVub2RkIiBmaWx0ZXI9InVybCgjZmlsdGVyNjMzOSkiIG9wYWNpdHk9Ii40OTgyNSIvPgogIDxwYXRoIGlkPSJyZWN0NjYxMiIgZD0ibTM4LjczNCAzN2gxLjYxNTVsMS4wNTcxIDFoLTEuNzE5OXoiIGZpbGw9InVybCgjbGluZWFyR3JhZGllbnQ2NjkyKSIgZmlsbC1ydWxlPSJldmVub2RkIi8+CiAgPHBhdGggaWQ9InBhdGg2MTUwIiBkPSJtMjMuNTYyIDMuNWMtMS4zNDE1LTAuMDAzNDI1LTIuNzEyOCAwLjI1MjM4LTQuMDYyNSAwLjgxMjVsMS42ODc1IDMuNWMtMS45NjQ3IDAuNDE3NzItMy43NjUyIDEuMjY2NC01LjMxMjUgMi40Mzc1bC0xLjMxMjUtMy44NzVjLTIuNzAwOSAxLjExNjYtNC41OTEgMy4wODg2LTUuNzE4OCA1LjU5MzhsNCAxLjQzNzVjLTEuMDk4NCAxLjYwOC0xLjgzNzcgMy40NjUtMi4xNTYyIDUuNDY4OGwtMy44NDM4LTEuODc1Yy0xLjEyMDIgMi42OTk0LTEuMDM2NSA1LjQzMTItMC4wNjI1IDhsMy45MDYyLTEuODQzOGMwLjMyMTM2IDEuOTkyMSAxLjA2MzQgMy44Mzc2IDIuMTU2MiA1LjQzNzVsLTMuOTY4OCAxLjM3NWMxLjExNjYgMi43MDA5IDMuMTE5OCA0LjU1OTggNS42MjUgNS42ODc1bDEuMzc1LTMuOTA2MmMxLjU0NzMgMS4xNzExIDMuMzQ3OCAyLjAxOTggNS4zMTI1IDIuNDM3NWwtMS42ODc1IDMuNWMyLjY5OTQgMS4xMjAyIDUuNDMxMiAxLjAzNjUgOCAwLjA2MjVsLTEuNTkzOC0zLjQwNjJjMS45NzYyLTAuMjgxMTEgMy44MDItMC45OTAzOSA1LjQwNjItMi4wMzEybDEuMjE4OCAzLjM0MzhjMi41MDUyLTEuMTI3NyA0LjUwODQtMi45ODY2IDUuNjI1LTUuNjg3NWwtMy4yMTg4LTEuMTI1YzEuMTE3My0xLjU1MzkgMS45MzctMy4zMzE3IDIuMzEyNS01LjI4MTJsMyAxLjQzNzVjMC45NzM5Ny0yLjU2ODggMS4wODktNS4zMDA2LTAuMDMxMjUtOGwtMyAxLjQ2ODhjLTAuMzc5MzQtMi4wMTgtMS4xMzE1LTMuODI1OC0yLjE4NzUtNS4zNzVsMy4xMjUtMS4wOTM4Yy0xLjEyNzctMi41MDUyLTIuOTg2Ni00LjUwODQtNS42ODc1LTUuNjI1bC0xLjA5MzggMy4xNTYyYy0xLjU5Mi0xLjAxLTMuNDQ5Mi0xLjY2MS01LjQ2ODgtMS45MDYybDEuNTkzOC0zLjM3NWMtMS4yODQ0LTAuNDg2OTktMi41OTYtMC43NDY1OC0zLjkzNzUtMC43NXptMC40Mzc1IDUuOTY4OGMzLjc0MjcgMCA2LjkyMTcgMS40MTUyIDkuMTI1IDQuMDkzOC02LjgwMzIgNC4wNDM4LTIwLjEwNCAxMS45MTktMTkuODEyIDExLjc1LTAuNTY3MzEtMS4zOTY0LTAuNzUtMi43MTEzLTAuNzUtNC4zMTI1IDAtNi42NDE3IDQuNzk1Ni0xMS41MzEgMTEuNDM4LTExLjUzMXptMTAuNTk0IDYuNjU2MmMwLjczMDM0IDEuNTUxOSAwLjkwNjI1IDMuMDQ0OSAwLjkwNjI1IDQuODc1IDAgNi42NDE3LTQuODU4MSAxMS41LTExLjUgMTEuNS0zLjk3MzUgMC03LjA5NC0xLjcxOTUtOS4yODEyLTQuNjg3NXoiIGZpbGw9InVybCgjcmFkaWFsR3JhZGllbnQ2NTgyKSIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9InVybCgjbGluZWFyR3JhZGllbnQ2MTU0KSIgc3Ryb2tlLXdpZHRoPSIxcHgiLz4KICA8cGF0aCBpZD0icGF0aDY0NjciIGQ9Im0yNC41IDIuNWMtMTAuNDg4IDAtMTkgOC4yODgtMTkgMTguNXM4LjUxMiAxOC41IDE5IDE4LjUgMTktOC4yODggMTktMTguNS04LjUxMi0xOC41LTE5LTE4LjV6bTAgM2M4LjgzMiAwIDE2IDYuOTQ0IDE2IDE1LjVzLTcuMTY4IDE1LjUtMTYgMTUuNWMtOC44MzIgMC0xNi02Ljk0NC0xNi0xNS41czcuMTY4LTE1LjUgMTYtMTUuNXoiIGZpbGw9InVybCgjbGluZWFyR3JhZGllbnQ2NDkzKSIgZmlsbC1ydWxlPSJldmVub2RkIiBzdHJva2U9InVybCgjbGluZWFyR3JhZGllbnQ2NDk1KSIvPgogIDxwYXRoIGlkPSJwYXRoNjUxMCIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMiwtMikiIGQ9Im0yMi41IDUuNTA3OGMtOS45NTcgMC0xNy45OTIgNy44NDAzLTE3Ljk5MiAxNy40OTJzOC4wMzUyIDE3LjQ5MiAxNy45OTIgMTcuNDkyYzkuOTU3IDAgMTcuOTkyLTcuODQwMyAxNy45OTItMTcuNDkycy04LjAzNTItMTcuNDkyLTE3Ljk5Mi0xNy40OTJ6IiBmaWxsPSJub25lIiBvcGFjaXR5PSIuMzc4OTUiIHN0cm9rZT0iI2ZmZiIvPgogIDxlbGxpcHNlIGlkPSJwYXRoNjE5MiIgdHJhbnNmb3JtPSJtYXRyaXgoNC40NDQ0IDAgMCAzLjgwOTUgLTc0Ljg4OSAtNjMuNjQzKSIgY3g9IjIyLjI1IiBjeT0iMjIuMjE5IiByeD0iLjU2MjUiIHJ5PSIuNjU2MjUiIGZpbGw9IiNiOWJiYjYiIGZpbGwtcnVsZT0iZXZlbm9kZCIgc3Ryb2tlPSIjNTU1NzUzIiBzdHJva2Utd2lkdGg9Ii4yNDMwMyIvPgogIDxlbGxpcHNlIGlkPSJwYXRoNjYwMiIgdHJhbnNmb3JtPSJtYXRyaXgoMS43Nzc4IDAgMCAxLjUyMzggLTE1LjU1NiAtMTIuODU3KSIgY3g9IjIyLjI1IiBjeT0iMjIuMjE5IiByeD0iLjU2MjUiIHJ5PSIuNjU2MjUiIGZpbGw9IiNlZWVlZWMiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPgogIDxwYXRoIGlkPSJwYXRoNjY5NCIgZD0ibTkuMjM0NCAzN2gtMS42MTU1bC0wLjk0Nzc2IDFoMS43MTk5eiIgZmlsbD0idXJsKCNsaW5lYXJHcmFkaWVudDY2OTYpIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz4KIDwvZz4KPC9zdmc+Cg=="


Hamster().generate()
