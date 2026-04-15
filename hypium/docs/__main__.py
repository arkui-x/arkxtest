import os.path

dir_path = os.path.dirname(__file__)
has_api_reference = False
for file in os.listdir(dir_path):
    if file.endswith(".md") and file.startswith("hypium"):
        print("Hypium API references path: %s" % os.path.join(dir_path, file))
        has_api_reference = True
        break

if not has_api_reference:
    print("No Hypium API references")
