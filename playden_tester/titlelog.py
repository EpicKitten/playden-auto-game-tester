"""Read Playden's title-<ID>.log digests.

Playden rewrites the digest after each session: one "== session-N.log" section
per session, newest first, each with its head and tail (the middle is left
out), then a "== reports" section with each session's size and end time.
Each session starts with a "PW_REPORT/1 ... time=<start>" line.
"""
import re
from dataclasses import dataclass, field

HEADER = re.compile(r"^== (session-\d+\.log)", re.MULTILINE)
REPORT = re.compile(r"^PW_REPORT/1 .*?\bprofile=(\S+).*?\btime=(\d+)", re.MULTILINE)
ENDED = re.compile(r"^(session-\d+\.log) bytes=(\d+) time=(\d+)", re.MULTILINE)
STEAM_PROFILE = re.compile(r"playden-steam-(\d+)")

# Lines that mean the game went wrong, with the label the result gets.
FATAL = [
    (re.compile(r"Crash!!!"), "crash"),
    (re.compile(r"Unhandled exception|unhandled exception"), "unhandled exception"),
    (re.compile(r"Assertion .* failed|assertion failed"), "assertion"),
    (re.compile(r"\bwine: could not load\b|err:module:import_dll"), "missing dll"),
    (re.compile(r"\bstatus=(?!0\b|ok\b)(-?\w+)\b.*\bstage="), "load stage failed"),
]
WINE_ERR = re.compile(r"WINE [0-9a-f]{4}:err:(\w+)")


@dataclass
class Session:
    name: str
    start: int
    end: int = 0
    profile: str = ""
    text: str = ""
    problems: list = field(default_factory=list)
    wine_errors: dict = field(default_factory=dict)

    @property
    def duration(self):
        return self.end - self.start if self.end >= self.start else 0

    @property
    def steam_app(self):
        match = STEAM_PROFILE.search(self.profile)
        return int(match.group(1)) if match else None

    def tail(self, lines=30):
        return "\n".join(self.text.rstrip().splitlines()[-lines:])


def parse(text):
    """The sessions in a digest, newest first."""
    ended = {name: int(time) for name, _, time in ENDED.findall(text)}
    marks = list(HEADER.finditer(text))
    reports_at = text.find("\n== reports")
    sessions = []
    for i, mark in enumerate(marks):
        stop = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        if mark.start() < reports_at < stop:
            stop = reports_at
        body = text[mark.start():stop]
        report = REPORT.search(body)
        if not report:
            continue
        session = Session(mark.group(1), int(report.group(2)), ended.get(mark.group(1), 0), report.group(1), body)
        analyse(session)
        sessions.append(session)
    sessions.sort(key=lambda s: s.start, reverse=True)
    return sessions


def analyse(session):
    seen = set()
    for line in session.text.splitlines():
        for pattern, label in FATAL:
            if label not in seen and pattern.search(line):
                seen.add(label)
                session.problems.append((label, line.strip()[:300]))
        match = WINE_ERR.search(line)
        if match:
            session.wine_errors[match.group(1)] = session.wine_errors.get(match.group(1), 0) + 1


def report_times(text):
    """The start times of every session in a digest."""
    return {int(time) for _, time in REPORT.findall(text)}


def steam_app(text):
    match = STEAM_PROFILE.search(text[:4096])
    return int(match.group(1)) if match else None
