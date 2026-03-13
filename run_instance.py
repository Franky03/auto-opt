import io, zipfile, requests

r = requests.get('https://neo.lcc.uma.es/vrp/wp-content/data/instances/kelly/kelly.zip', timeout=30)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    for name in z.namelist():
        print(repr(name))