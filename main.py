import requests, json, os, re, xmltodict, time
from tabulate import tabulate

session = requests.Session()
with open("login.json", "r") as file1:
    login = json.loads(file1.read())

session.post("https://www.stockmarketgame.org/cgi-bin/hailogin", data=login)

response = session.get("https://www.stockmarketgame.org/cgi-bin/haipage/page.html?tpl=Administration/game/a_trad/tdpositions")

fixedresponse = re.sub('(.|\n)*?\/message>', '<ROOT>', response.text)
fixedresponse = re.sub('<\/TDRESULTS>(.|\n)*', '</ROOT>', fixedresponse)
fixedresponse = re.sub('TYEAR', 'TYYEAR', fixedresponse)

o = xmltodict.parse(fixedresponse)

symbols = ''
updates = []

for i in o['ROOT']['POSITIONDATA']:
    symbols = symbols + i['SYMBOL'] + ','
    updates.append(0)

symbols = symbols[:-1]

while True:
    start_time = time.time()
    x = requests.get(f"https://us-east-1.aws.data.mongodb-api.com/app/polygon-api-xtron/endpoint/summaries?tickers={symbols}")
    y = json.loads(x.text)

    head = ["price", "change", "ticker", "name", "updated"]
    data = []

    for info in y['results']:
        percent = str(info['session']['change_percent']) + "%"
        price = str(info['price'])
        ticker = str(info['ticker'])
        updated = info['last_updated'] // 1000000000
        if percent[0] == '-':
            percent = "\033[0;31m" + percent + "\033[0;0m"
        else:
            percent = "\033[0;32m" + percent + "\033[0;0m"
        if updated != updates[y['results'].index(info)]:
            price = "\033[0;34m" + price + "\033[0;0m"
            ticker = "\033[0;34m" + ticker + "\033[0;0m"
            updates[y['results'].index(info)] = updated
        data.append([price, percent, ticker, str(info['name']), time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated))])

    os.system('clear')
    print(tabulate(data, headers=head, tablefmt="grid", numalign="left"))
    print((time.time() - start_time))