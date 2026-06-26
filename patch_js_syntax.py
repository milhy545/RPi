import re

with open("webserver.py", "r") as f:
    content = f.read()

# I used a multiline string in JavaScript for mixerHtml+='<style>... \n .sr-only ...</style>';
# JavaScript single-quoted strings don't support newlines!
content = content.replace("} }\n.sr-only", "} } .sr-only")

with open("webserver.py", "w") as f:
    f.write(content)
