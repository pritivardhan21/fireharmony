import re
p = "src/App.tsx"
s = open(p, encoding="utf-8", newline="").read()
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

def sub(pattern, new):
    global s
    s, n = re.subn(pattern, lambda m: new, s, count=1, flags=re.S)
    print(n, pattern[:40])

sub(r"Do two families of satellites tell.*?\{meta\.end_year\}",
    "Do two satellite families tell the same story about crop-residue burning? Punjab–Haryana, {meta.start_year}–{meta.end_year}")
sub(r"          \{meta\.start_year >= 2012 && \(.*?\n          \)\}\n", "")
sub(r"      \{/\* Plain-language summary for first-time viewers \*/\}.*?(?=      \{/\* Headline strip)", "")
sub(r"Satellite daytime detections of October.*?on its own\.",
    "October–November daytime detections fell about 90% from 2021 to 2025. This is consistent with burning moving to times between satellite passes, which our data cannot prove on its own. Pick an area below to explore.")
sub(r"S-NPP daytime detections, Oct–Nov, study box, 2021 → 2025 \(−90%\)", "S-NPP daytime detections, Oct–Nov, 2021 → 2025 (−90%)")
sub(r"Aqua median daytime pass \(IST\), Oct–Nov, 2021 → 2025; S-NPP stayed near 13:42", "Aqua median daytime pass (IST); S-NPP stays near 13:42")
sub(r"S-NPP night detections, Oct–Nov, 2021 → 2025: too few to absorb the daytime loss", "S-NPP night detections: too few to absorb the loss")

if crlf:
    s = s.replace("\n", "\r\n")
open(p, "w", encoding="utf-8", newline="").write(s)
print("patched")
