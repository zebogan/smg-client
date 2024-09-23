import requests, json, os, re, xmltodict, time, tabulate, sys

try:
    # open login creds
    with open("login.json", "r") as file1:
        login = json.loads(file1.read())
except:
    print("input login info")
    user = input("username: ")
    password = input("password: ")
    logindata = {
        "ACCOUNTNO": user,
        "USER_PIN": password,
        "SECURITY_STRING": ""
    }
    with open("login.json", "w") as file2:
        json.dump(logindata, file2)
    print("run program again")
    sys.exit()

# for keeping login cookie
session = requests.Session()
# send login
loginResponse = session.post("https://www.stockmarketgame.org/cgi-bin/hailogin", data=login)
if "invalid" in loginResponse.text:
    print("invalid username/password, edit login.json to repair")
    sys.exit()

print("logged in")

# get list of symbols that account holds
symbolsResponse = session.get("https://www.stockmarketgame.org/cgi-bin/haipage/page.html?tpl=Administration/game/a_trad/tdpositions")

# edit html to be able to parse xml data
fixedSymbolsResponse = re.sub('(.|\n)*?\/message>', '<ROOT>', symbolsResponse.text)
fixedSymbolsResponse = re.sub('<\/TDRESULTS>(.|\n)*', '</ROOT>', fixedSymbolsResponse)
fixedSymbolsResponse = re.sub('TYEAR', 'TYYEAR', fixedSymbolsResponse)

print("got held symbols")

# convert xml to a dict (bad variable name i know)
symbolsXML = xmltodict.parse(fixedSymbolsResponse)

# string of symbols for getting info
symbols = ''
symbolsList = []
# timestamp of last price change
updates = []

for i in symbolsXML['ROOT']['POSITIONDATA']:
    if i['SYMBOL'] in symbolsList:
        symbolsXML['ROOT']['POSITIONDATA'].remove(i)
    else:
        symbolsList.append(i['SYMBOL'])

for i in symbolsXML['ROOT']['POSITIONDATA']:
    symbols = symbols + i['SYMBOL'] + ','
    updates.append(0)

# delete trailing comma
symbols = symbols[:-1]

# get info about holdings, for original price
holdingsPriceResponse = session.get(f"https://www.stockmarketgame.org/cgi-bin/haipage/page.html?tpl=Administration/game/a_trad/cont_acctholdings&_={round(time.time() * 1000)}")

# convert html to xml
fixedHPriceResponse = re.sub('(.|\n)*?\/account_info>\n', '', holdingsPriceResponse.text)
fixedHPriceResponse = re.sub('\n<\/response>(.|\n)*', '', fixedHPriceResponse)

# convert xml to a dict (bad variable name i know) part 2
hPriceXML = xmltodict.parse(fixedHPriceResponse)

print("got original prices")

# original prices of holdings
holdingsPrices = {}
# quantity of held stock
quantity = {}

for j in hPriceXML['transactions']['record']:
    holdingsPrices[j['ticker']] = j['netcost_pershare']
    quantity[j['ticker']] = j['shares_value']

# for speeding up polygon requests
polygonSession = requests.Session()

while True:
    start_time = time.time()

    # for piggybacking off of their polygon instance bc im lazy
    # get info about current prices of holdings

    x = polygonSession.get(f"https://us-east-1.aws.data.mongodb-api.com/app/polygon-api-xtron/endpoint/summaries?tickers={symbols}")
    request_time = time.time()
    y = json.loads(x.text)
    # sort by ticker instead of by name
    results = sorted(y['results'], key=lambda d: d['ticker'])

    head = ["price", "change", "profit", "ticker", "purchase", "name", "updated"]
    data = []

    for info in results:
        percent = str(info['session']['change_percent']) + "%"
        price = str(info['price'])
        ticker = str(info['ticker'])
        updated = info['last_updated'] // 1000000000
        originalPrice = holdingsPrices[ticker]
        # calculate profit of each stock
        profit = str((info['price'] - float(originalPrice)) * int(quantity[ticker]))
        if percent[0] == '-':
            # make red if negative
            percent = "\033[0;31m" + percent + "\033[0;0m"
        else:
            # make green
            percent = "\033[0;32m" + percent + "\033[0;0m"
        if updated != updates[results.index(info)]:
            # if updated since last refresh, make blue
            price = "\033[0;34m" + price + "\033[0;0m"
            ticker = "\033[0;34m" + ticker + "\033[0;0m"
            profit = "\033[0;34m" + profit + "\033[0;0m"
            updates[results.index(info)] = updated
        data.append([price, percent, profit, ticker, originalPrice, str(info['name'])[0:50], time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated))])
    
    # make table and print
    table = tabulate.tabulate(data, headers=head, tablefmt="outline", numalign="left")
    os.system('clear')
    print(table)

    final_time = time.time() - start_time
    print(request_time - start_time)
    print(final_time - (request_time - start_time))