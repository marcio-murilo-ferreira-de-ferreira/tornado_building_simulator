import re, glob
path = glob.glob('tornado-control-center/dist/assets/index*.js')[0]
text = open(path, 'r', encoding='utf-8').read()

m = re.search(r'v==="topsis"\?n\|\|e\?\.winner_topsis:t', text)
if m:
    print("MATCH:", m.group(0))
    text = text.replace(m.group(0), 'v==="topsis"?R.is_topsis_winner:t')
    open(path, 'w', encoding='utf-8').write(text)
    print("PATCHED")
else:
    print("NOT FOUND")
