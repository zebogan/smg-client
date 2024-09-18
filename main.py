import requests, json, os, re, xmltodict, time
from tabulate import tabulate

session = requests.Session()
with open("login.json", "r") as file1:
    login = json.loads(file1.read())

session.post("https://www.stockmarketgame.org/cgi-bin/hailogin", data=login)

symbolsResponse = session.get("https://www.stockmarketgame.org/cgi-bin/haipage/page.html?tpl=Administration/game/a_trad/tdpositions")

fixedSymbolsResponse = re.sub('(.|\n)*?\/message>', '<ROOT>', symbolsResponse.text)
fixedSymbolsResponse = re.sub('<\/TDRESULTS>(.|\n)*', '</ROOT>', fixedSymbolsResponse)
fixedSymbolsResponse = re.sub('TYEAR', 'TYYEAR', fixedSymbolsResponse)

symbolsXML = xmltodict.parse(fixedSymbolsResponse)

symbols = ''
symbolsDict = []
updates = []

for i in symbolsXML['ROOT']['POSITIONDATA']:
    symbols = symbols + i['SYMBOL'] + ','
    symbolsDict.append(i['SYMBOL'])
    updates.append(0)

symbols = symbols[:-1]

holdingsPriceResponse = session.get(f"https://www.stockmarketgame.org/cgi-bin/haipage/page.html?tpl=Administration/game/a_trad/cont_acctholdings&_={round(time.time() * 1000)}")

fixedHPriceResponse = re.sub('(.|\n)*?\/account_info>\n', '', holdingsPriceResponse.text)
fixedHPriceResponse = re.sub('\n<\/response>(.|\n)*', '', fixedHPriceResponse)

hPriceXML = xmltodict.parse(fixedHPriceResponse)

holdingsPrices = []

print(hPriceXML)

#https://www.stockmarketgame.org/cgi-bin/haipage/page.html?tpl=Administration/game/a_trad/cont_acctholdings&_=1726677788313


# while True:
#     x = requests.get(f"https://us-east-1.aws.data.mongodb-api.com/app/polygon-api-xtron/endpoint/summaries?tickers={symbols}")
#     y = json.loads(x.text)
#     results = sorted(y['results'], key=lambda d: d['ticker'])

#     head = ["price", "change", "ticker", "name", "updated"]
#     data = []

#     for info in results:
#         percent = str(info['session']['change_percent']) + "%"
#         price = str(info['price'])
#         ticker = str(info['ticker'])
#         updated = info['last_updated'] // 1000000000
#         if percent[0] == '-':
#             percent = "\033[0;31m" + percent + "\033[0;0m"
#         else:
#             percent = "\033[0;32m" + percent + "\033[0;0m"
#         if updated != updates[results.index(info)]:
#             price = "\033[0;34m" + price + "\033[0;0m"
#             ticker = "\033[0;34m" + ticker + "\033[0;0m"
#             updates[results.index(info)] = updated
#         data.append([price, percent, ticker, str(info['name']), time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated))])
#     table = tabulate(data, headers=head, tablefmt="outline", numalign="left")
#     os.system('clear')
#     print(table)