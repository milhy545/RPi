import re
pattern = r"^(?P<type>[a-z]+)(\((?P<scope>.+)\))?(?P<breaking>!)?: (?P<subject>.+)$"
text1 = "feat(ui): 🎨 Palette: Dynamic translations for icon-only buttons"
text2 = "feat: Palette: Dynamic translations for icon-only buttons"
text3 = "feat: 🎨 Palette: Dynamic translations for icon-only buttons"
print(bool(re.match(pattern, text1)))
print(bool(re.match(pattern, text2)))
print(bool(re.match(pattern, text3)))
