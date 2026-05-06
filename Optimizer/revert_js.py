import glob

path = glob.glob('tornado-control-center/dist/assets/index*.js')[0]
text = open(path, 'r', encoding='utf-8').read()

text = text.replace('v==="topsis"?R.is_topsis_winner:t', 'v==="topsis"?n||e?.winner_topsis:t')

open(path, 'w', encoding='utf-8').write(text)
print("JS Reverted Successfully!")
