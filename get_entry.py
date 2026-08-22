import urllib.request
import re
import json

url = 'https://docs.google.com/forms/d/e/1FAIpQLSfM5yQr_DqRjjVdn2nj8i_Zo7Ng2KGla2o3H_-NjJIUYrIAMg/viewform'
html = urllib.request.urlopen(url).read().decode('utf-8')

# Find the FB_PUBLIC_LOAD_DATA_ JSON block
match = re.search(r'var FB_PUBLIC_LOAD_DATA_ = (\[.*?\]);\n', html)
if match:
    data = json.loads(match.group(1))
    # data[1][1] contains the list of questions
    for q in data[1][1]:
        q_id = q[0]
        q_title = q[1]
        # q[4][0][0] contains the entry ID
        entry_id = q[4][0][0]
        print(f"Question: {q_title} -> entry.{entry_id}")
else:
    print("Could not find FB_PUBLIC_LOAD_DATA_")
