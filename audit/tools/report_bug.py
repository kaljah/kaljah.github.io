"""
Atomically allocate the next BUG ID and append a finding to AUDIT_FINDINGS.md.

    python C:/Users/samsung/Desktop/H2/audit/tools/report_bug.py <draft.md>

<draft.md> must start with a line  "# BUG-XXX — <title>"  (literal XXX); the rest follows the
required template. The script replaces XXX with the next free number, appends it to
C:/Users/samsung/Desktop/H2/AUDIT_FINDINGS.md under an exclusive lock, and prints the ID.

To ADD EVIDENCE to an existing bug (dedup) instead of creating a new one:

    python .../report_bug.py --confirm BUG-007 <note.md>

appends a "### Additional confirmation (BUG-007)" block to the addenda section.
"""
import os
import re
import sys
import time

FINDINGS = os.environ.get("AUDIT_FINDINGS_PATH", r"C:/Users/samsung/Desktop/H2/AUDIT_FINDINGS.md")
LOCK = FINDINGS + ".lock"
HEADER = "# AUDIT FINDINGS\n\nLive defect log. Each entry was appended the moment it was confirmed.\n\n"


def locked(fn):
    for _ in range(600):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() - os.path.getmtime(LOCK) > 60:
                try:
                    os.remove(LOCK)
                except OSError:
                    pass
            time.sleep(0.1)
    else:
        sys.exit("could not acquire lock")
    try:
        return fn()
    finally:
        os.close(fd)
        os.remove(LOCK)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--confirm":
        bug_id, path = args[1], args[2]
        body = open(path, encoding="utf-8").read().strip()

        def do():
            with open(FINDINGS, "a", encoding="utf-8") as f:
                f.write(f"\n\n### Additional confirmation ({bug_id})\n\n{body}\n")
            return bug_id

        print(locked(do))
        return

    body = open(args[0], encoding="utf-8").read().strip()
    if not re.match(r"^# BUG-XXX", body):
        sys.exit("draft must start with '# BUG-XXX — <title>'")

    def do():
        text = open(FINDINGS, encoding="utf-8").read() if os.path.exists(FINDINGS) else HEADER
        nums = [int(n) for n in re.findall(r"^# BUG-(\d{3,})", text, re.M)]
        new_id = f"BUG-{(max(nums) + 1 if nums else 1):03d}"
        entry = body.replace("BUG-XXX", new_id, 1)
        with open(FINDINGS, "w" if not os.path.exists(FINDINGS) else "a", encoding="utf-8") as f:
            if not os.path.exists(FINDINGS) or f.tell() == 0:
                f.write(HEADER)
            f.write("\n\n---\n\n" + entry + "\n")
        return new_id

    print(locked(do))


if __name__ == "__main__":
    main()
