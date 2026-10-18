import re

regex = re.compile(r'^(?P<type>[a-z]+)(\((?P<scope>.+)\))?(?P<breaking>!)?: (?P<subject>.+)$')

titles = [
    "perf: ⚡ Bolt: [Optimize run_sys_cmd using exec instead of shell]",
    "⚡ Bolt: [Optimize run_sys_cmd using exec instead of shell]",
    "perf(tui): ⚡ Bolt: [Optimize run_sys_cmd using exec instead of shell]",
    "perf: bolt"
]

for title in titles:
    m = regex.match(title)
    if m:
        print(f"PASS: {title}")
    else:
        print(f"FAIL: {title}")
