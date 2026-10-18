const regex = /^(?<type>[a-z]+)(\((?<scope>.+)\))?(?<breaking>!)?: (?<subject>.+)$/;
const titles = [
  "refactor(ui): palette added aria-labels to icon-only modal close buttons",
  "🎨 Palette: Add aria-labels to icon-only modal close buttons",
  "refactor(ui): 🎨 Palette: Add aria-labels to icon-only modal close buttons"
];

for (const title of titles) {
  const match = regex.exec(title);
  if (match) {
    console.log(`✅ Passed: "${title}"\n   Type: ${match.groups.type}, Scope: ${match.groups.scope || 'none'}, Subject: ${match.groups.subject}`);
  } else {
    console.log(`❌ Failed: "${title}"`);
  }
}
