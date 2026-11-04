"""An MCP server over stdin and stdout, so agents can run the console and its tests through tools. Standard library
only: MCP's stdio transport is one JSON-RPC message per line.
"""
import json
import sys

from .rig import jpeg_text

PROTOCOL = "2025-06-18"
TEXT, NUMBER, BOOL = {"type": "string"}, {"type": "number"}, {"type": "boolean"}
PATH = {"type": "string", "description": "absolute path on the console"}
LOCAL = {"type": "string", "description": "path on this PC"}
INTEGERS = {"type": "array", "items": {"type": "integer"}}


class Content(list):
    """MCP content items, as opposed to a list that is the tool's answer (file rows have a "type" of their own)."""


def schema(required=(), **properties):
    return {"type": "object", "properties": properties, "required": list(required)}


def _screenshot(rig, args):
    data, path = rig.screenshot(args.get("path"))
    return Content([{"type": "image", "data": jpeg_text(data), "mimeType": "image/jpeg"},
                    {"type": "text", "text": f"Full frame: {path}"}])


def _delete(rig, args):
    return rig.file_delete(args["path"], args.get("dry_run", True))


def _power(rig, args):
    if args.get("confirm") is not True:
        raise ValueError("power needs confirm: true, because a restart loses the jailbreak until it's loaded by hand")
    return rig.power(args["action"])


# name: (description, input schema, handler(rig, args))
TOOLS = {
    "status": ("Which console services answer, running titles, pad state and campaign progress. Call this first.",
               schema(), lambda r, a: r.status()),
    "start_services": ("Start ps5-web-file-manager and padd if they aren't running. padd then needs cross pressed on "
                       "the \"Who's using this controller?\" dialog.", schema(), lambda r, a: r.start_services()),
    "screenshot": ("Take a picture of the console's screen through the capture card.",
                   schema(path=LOCAL), _screenshot),
    "read_screen": ("OCR the screen: its text with positions, and Playden's focused item.",
                    schema(), lambda r, a: r.read_screen()),
    "screen_check": ("Tell whether the picture is black, still or moving.",
                     schema(seconds=NUMBER), lambda r, a: r.screen_check(a.get("seconds", 3.0))),
    "press": ("Press pad buttons together: cross, circle, square, triangle, l1, r1, l2, r2, up, down, left, right, "
              "options, l3, r3, touchpad.",
              schema(["buttons"], buttons={"type": "array", "items": TEXT}, repeat={"type": "integer"}, hold=NUMBER,
                     gap=NUMBER),
              lambda r, a: r.press(a["buttons"], a.get("repeat", 1), a.get("hold", 0.12), a.get("gap", 0.4))),
    "stick": ("Move a stick for a moment. x and y run from -1 to 1; up and left are negative.",
              schema(["side", "x", "y"], side={"enum": ["left", "right"]}, x=NUMBER, y=NUMBER, seconds=NUMBER),
              lambda r, a: r.stick(a["side"], a["x"], a["y"], a.get("seconds", 0.3))),
    "home": ("Suspend the running game and show the PS5's Home.", schema(), lambda r, a: r.home()),
    "games": ("List the Playden games installed on the console.", schema(), lambda r, a: r.games()),
    "launch": ("Start a title by ID, for example FAKE78001.", schema(["title"], title=TEXT),
               lambda r, a: r.launch(a["title"])),
    "close_app": ("Close the running game.", schema(), lambda r, a: r.close_app()),
    "title_log": ("Read the end of a title's Playden log.", schema(["title"], title=TEXT, tail={"type": "integer"}),
                  lambda r, a: r.title_log(a["title"], a.get("tail", 20000))),
    "runtime_log": ("Read the end of Playden's runtime.log.", schema(tail={"type": "integer"}),
                    lambda r, a: r.runtime_log(a.get("tail", 20000))),
    "file_list": ("List a console folder.", schema(["path"], path=PATH), lambda r, a: r.file_list(a["path"])),
    "file_read": ("Read a text file on the console.", schema(["path"], path=PATH), lambda r, a: r.file_read(a["path"])),
    "file_write": ("Write a text file on the console.", schema(["path", "text"], path=PATH, text=TEXT),
                   lambda r, a: r.file_write(a["path"], a["text"])),
    "file_upload": ("Copy a file from this PC to the console.", schema(["local", "path"], local=LOCAL, path=PATH),
                    lambda r, a: r.file_upload(a["local"], a["path"])),
    "file_download": ("Copy a file or folder from the console to this PC. Returns the bytes saved.",
                      schema(["path", "local"], path=PATH, local=LOCAL),
                      lambda r, a: r.file_download(a["path"], a["local"])),
    "file_delete": ("Permanently delete inside the allowed folders. dry_run is true by default and only shows what "
                    "would go; pass false only when the user asked for this delete.",
                    schema(["path"], path=PATH, dry_run=BOOL), _delete),
    "processes": ("List the console's processes.", schema(), lambda r, a: r.processes()),
    "process_kill": ("Stop a process by ID. Payload Manager and elfldr are refused.",
                     schema(["pid"], pid={"type": "integer"}), lambda r, a: r.process_kill(a["pid"])),
    "payload_list": ("List the payloads in Payload Manager's library.", schema(), lambda r, a: r.payload_list()),
    "payload_start": ("Start a payload from Payload Manager's library.", schema(["path"], path=PATH),
                      lambda r, a: r.payload_start(a["path"])),
    "payload_send": ("Run a local ELF on the console through elfldr, without writing to its disk.",
                     schema(["local"], local=LOCAL), lambda r, a: r.payload_send(a["local"])),
    "power": ("Restart the console, or put it in rest mode or turn it off. Only when the user asked. Everything "
              "stops responding, nothing here can wake the console, and the jailbreak has to be loaded again by hand "
              "after a restart. Needs confirm: true.",
              schema(["action", "confirm"], action={"enum": ["restart", "standby", "off"]}, confirm=BOOL), _power),
    "campaign_start": ("Start testing games in the background: download, test, report, uninstall. Runs for days and "
                       "outlives this server. order is players (default) or size; only is a list of Steam app IDs.",
                       schema(only=INTEGERS, limit={"type": "integer"}, order={"enum": ["players", "size"]},
                              watch={"type": "integer"}),
                       lambda r, a: {"pid": r.campaign_start(a.get("only"), a.get("limit"), a.get("order", "players"),
                                                             a.get("watch"))}),
    "campaign_status": ("Whether a campaign runs, its result counts and the end of its log.",
                        schema(lines={"type": "integer"}),
                        lambda r, a: {**r.campaign_status(), "log": r.campaign_log(a.get("lines", 40))}),
    "campaign_stop": ("Stop the campaign before its next game. It keeps going until the current game is done.",
                      schema(), lambda r, a: r.campaign_stop()),
    "update_lists": ("Rebuild the lists of games to test from Playden's tracker, Steam and the other sources.",
                     schema(), lambda r, a: r.update_lists()),
}


def call_tool(rig, name, args):
    """The result of a tools/call. A failed tool is a result with isError, so the agent can read why."""
    if name not in TOOLS:
        return {"content": [{"type": "text", "text": f"no tool called {name}"}], "isError": True}
    try:
        value = TOOLS[name][2](rig, args)
    except Exception as error:  # noqa: BLE001 - whatever a console service raised goes back to the agent
        return {"content": [{"type": "text", "text": f"{name}: {error}"}], "isError": True}
    if isinstance(value, Content):
        return {"content": list(value)}
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return {"content": [{"type": "text", "text": text if value is not None else "done"}]}


def handle(rig, message):
    """The reply to one JSON-RPC message, or None for a notification."""
    method, ident = message.get("method"), message.get("id")
    if ident is None:
        return None
    if method == "initialize":
        version = (message.get("params") or {}).get("protocolVersion") or PROTOCOL
        result = {"protocolVersion": version, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "playden-tester", "version": "0.1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": name, "description": text, "inputSchema": shape}
                            for name, (text, shape, _) in TOOLS.items()]}
    elif method == "tools/call":
        params = message.get("params") or {}
        result = call_tool(rig, params.get("name"), params.get("arguments") or {})
    else:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"no method {method}"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def serve(rig, stdin=None, stdout=None):
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    sys.stdout = sys.stderr  # stdout carries the protocol: a stray print must not land there
    for line in stdin:
        if not line.strip():
            continue
        try:
            reply = handle(rig, json.loads(line))
        except ValueError as error:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(error)}}
        if reply:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
