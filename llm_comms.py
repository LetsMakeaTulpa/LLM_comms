#!/usr/bin/env python3
"""
llm_comms — the AI mesh envelope tool.

Any AI to any AI, via copy-paste. No APIs, no auth, no vendor.
The envelope is the product; the transport is you.

Commands:
    send      compose a handoff envelope
    reply     compose a return envelope (swaps from/to, links reply-to)
    validate  check an envelope is well-formed
    grade     grade a return (claim-verification verdicts) and log it
    log       show the exchange log (the mesh's memory)

Stdlib only. Python 3.8+.
"""
import argparse
import datetime
import json
import os
import re
import sys

VERSION = "1.0.0"
VERDICTS = ("VERIFIED", "SUPPORTED", "CONTESTED", "STALE", "UNSOURCED")
SECTIONS = ("TASK", "CONTEXT", "RETURN FORMAT", "BOUNDARY")


def home():
    """Mesh home directory: $LLM_COMMS_HOME or ./mesh."""
    return os.environ.get("LLM_COMMS_HOME", os.path.join(os.getcwd(), "mesh"))


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_id():
    """Sequence ID = highest existing envelope number + 1."""
    h = home()
    nums = [0]
    if os.path.isdir(h):
        for f in os.listdir(h):
            m = re.match(r"^(\d{4})_", f)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1


def envelope_path(eid, frm, to):
    safe = lambda s: re.sub(r"[^a-zA-Z0-9-]", "-", s)
    return os.path.join(home(), "%04d_%s_to_%s.md" % (eid, safe(frm), safe(to)))


def write_envelope(frm, to, task, context="", fmt="plain markdown", boundary="", reply_to=None):
    os.makedirs(home(), exist_ok=True)
    eid = next_id()
    lines = ["---",
             "id: %04d" % eid,
             "from: %s" % frm,
             "to: %s" % to,
             "date: %s" % now_iso()]
    if reply_to:
        lines.append("reply-to: %s" % reply_to)
    lines += ["---", "",
              "# HANDOFF", "",
              "## TASK", task.strip(), "",
              "## CONTEXT", context.strip() or "(none)", "",
              "## RETURN FORMAT", fmt.strip() or "plain markdown", "",
              "## BOUNDARY", boundary.strip() or "(none)", ""]
    path = envelope_path(eid, frm, to)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return eid, path


def parse_envelope(path):
    """Return (header dict, sections dict). Raises ValueError on malformed structure."""
    if not os.path.isfile(path):
        raise ValueError("file not found: %s" % path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        raise ValueError("missing frontmatter (file must start with ---)")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("unterminated frontmatter")
    header = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            header[k.strip()] = v.strip()
    body = text[end + 4:]
    sections = {}
    current = None
    for line in body.splitlines():
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            current = m.group(1).strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    for k in list(sections):
        sections[k] = "\n".join(sections[k]).strip()
    return header, sections


def validate_envelope(path):
    """Full structural check. Raises ValueError with the reason on failure."""
    header, sections = parse_envelope(path)
    missing = [f for f in ("id", "from", "to", "date") if f not in header or not header[f]]
    if missing:
        raise ValueError("missing header fields: %s" % ", ".join(missing))
    for s in SECTIONS:
        if s not in sections:
            raise ValueError("missing section: %s" % s)
    if not sections["TASK"]:
        raise ValueError("empty TASK section (a handoff with no task is not a handoff)")
    return header, sections


def log_path():
    return os.path.join(home(), "log.jsonl")


def log_append(entry):
    os.makedirs(home(), exist_ok=True)
    with open(log_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_read():
    if not os.path.isfile(log_path()):
        return []
    out = []
    with open(log_path(), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def summarize(text, width=48):
    flat = " ".join(text.split())
    return flat[:width] + ("..." if len(flat) > width else "")


# ---------------------------------------------------------------- commands

def cmd_send(args):
    eid, path = write_envelope(args.from_node, args.to, args.task,
                               context=args.context, fmt=args.format,
                               boundary=args.boundary)
    print("envelope %04d  %s -> %s" % (eid, args.from_node, args.to))
    print("file: %s" % path)
    print("next: paste the file's contents into the %s chat. When it answers," % args.to)
    print("      save the answer, then: llm_comms.py grade <file> --verdict <verdict>")


def cmd_reply(args):
    try:
        header, _ = validate_envelope(args.envelope)
    except ValueError as e:
        print("FAIL: %s" % e)
        sys.exit(1)
    frm, to = header["to"], header["from"]
    eid, path = write_envelope(frm, to, args.task,
                               context=args.context, fmt=args.format,
                               boundary=args.boundary, reply_to=header["id"])
    print("reply envelope %04d  %s -> %s  (reply-to %s)" % (eid, frm, to, header["id"]))
    print("file: %s" % path)


def cmd_validate(args):
    try:
        header, sections = validate_envelope(args.envelope)
    except ValueError as e:
        print("FAIL: %s" % e)
        sys.exit(1)
    print("PASS  %s  (%s -> %s, %s)" % (header["id"], header["from"], header["to"], header["date"]))
    print("task: %s" % summarize(sections["TASK"]))
    sys.exit(0)


def cmd_grade(args):
    try:
        header, sections = validate_envelope(args.envelope)
    except ValueError as e:
        print("FAIL: %s" % e)
        sys.exit(1)
    verdict = args.verdict.upper()
    if verdict not in VERDICTS:
        print("verdict must be one of: %s" % ", ".join(VERDICTS))
        sys.exit(2)
    entry = {
        "id": header["id"],
        "ts": now_iso(),
        "from": header["from"],
        "to": header["to"],
        "task": summarize(sections["TASK"]),
        "verdict": verdict,
        "notes": summarize(args.notes, 120),
    }
    log_append(entry)
    print("graded  %s  (%s -> %s): %s" % (header["id"], header["from"], header["to"], verdict))
    print("logged. The mesh remembers. Run `llm_comms.py log` to see the record.")


def cmd_log(args):
    entries = log_read()
    if args.node:
        n = args.node.lower()
        entries = [e for e in entries if n in (e.get("from", "").lower(), e.get("to", "").lower())]
    if not entries:
        print("no exchanges logged yet. The mesh is young.")
        return
    fmt = "%-6s %-20s %-4s %-5s %-12s %s"
    print(fmt % ("ID", "DATE", "FROM", "TO", "VERDICT", "TASK"))
    for e in entries:
        date = (e.get("ts") or "")[:10]
        print(fmt % (e.get("id", "?"), date, e.get("from", "?")[:4],
                     e.get("to", "?")[:4], e.get("verdict", "?"),
                     e.get("task", "")))
    counts = {}
    for e in entries:
        counts[e.get("verdict", "?")] = counts.get(e.get("verdict", "?"), 0) + 1
    print("\n%d exchange(s): %s" % (len(entries),
          ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items()))))


def main():
    p = argparse.ArgumentParser(prog="llm_comms",
                                 description="The AI mesh envelope tool — any AI to any AI, via copy-paste.")
    p.add_argument("--version", action="version", version="llm_comms %s" % VERSION)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("send", help="compose a handoff envelope")
    s.add_argument("--to", required=True, help="target node (e.g. qwen, claude, kimi)")
    s.add_argument("--from", dest="from_node", default="local", help="source node (default: local)")
    s.add_argument("--task", required=True, help="one verb, one object, one done-when")
    s.add_argument("--context", default="", help="compressed state the receiver needs")
    s.add_argument("--format", dest="format", default="plain markdown", help="what the return must look like")
    s.add_argument("--boundary", default="", help="what NOT to do with this")
    s.set_defaults(func=cmd_send)

    s = sub.add_parser("reply", help="compose a return envelope for an existing handoff")
    s.add_argument("envelope", help="path to the envelope being answered")
    s.add_argument("--task", required=True, help="the ask for the return trip")
    s.add_argument("--context", default="")
    s.add_argument("--format", dest="format", default="plain markdown")
    s.add_argument("--boundary", default="")
    s.set_defaults(func=cmd_reply)

    s = sub.add_parser("validate", help="check an envelope is well-formed")
    s.add_argument("envelope")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("grade", help="grade a return with a claim-verification verdict")
    s.add_argument("envelope")
    s.add_argument("--verdict", required=True, help="one of: %s" % ", ".join(VERDICTS))
    s.add_argument("--notes", default="", help="one line: what the grade is based on")
    s.set_defaults(func=cmd_grade)

    s = sub.add_parser("log", help="show the exchange log")
    s.add_argument("--node", default=None, help="filter by node (from or to)")
    s.set_defaults(func=cmd_log)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
