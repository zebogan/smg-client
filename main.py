import requests, json, os, re, xmltodict, time, tabulate, sys

timeStats = {
    "iteration": 0,
    "totalNet": 0,
    "totalProgram": 0,
    "minNet": 0,
    "maxNet": 0,
    "minProgram": 0,
    "maxProgram": 0
}

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
    avgStats = [0, 0]
    start_time = time.time()

    # for piggybacking off of their polygon instance bc im lazy
    x = polygonSession.get(f"https://us-east-1.aws.data.mongodb-api.com/app/polygon-api-xtron/endpoint/summaries?tickers={symbols}")
    
    request_time = time.time()
    y = json.loads(x.text)
    # sort by ticker instead of by name
    results = sorted(y['results'], key=lambda d: d['ticker'])

    head = ["price", "change", "profit", "ticker", "purchase", "held", "name", "updated"]
    data = []

    for info in results:
        percent = str(info['session']['change_percent']) + "%"
        price = str(info['price'])
        ticker = str(info['ticker'])
        updated = info['last_updated'] // 1000000000
        originalPrice = holdingsPrices[ticker]

        # calculate profit of each stock
        profit = str(round((info['price'] - float(originalPrice)) * int(quantity[ticker]), 2))

        currentQuantity = quantity[ticker]
        avgStats[0] += float(info['session']['change_percent'])
        avgStats[1] += float(profit)

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

        data.append([price, percent, profit, ticker, originalPrice, currentQuantity, str(info['name'])[0:50], time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated))])

    avgStats[0] = round(avgStats[0], 4)
    avgStats[0] = str(avgStats[0]) + "%"
    if avgStats[0][0] == '-': 
        # make red if negative
        avgStats[0] = "\033[0;31m" + avgStats[0] + "\033[0;0m"
    else:
        # make green
        avgStats[0] = "\033[0;32m" + avgStats[0] + "\033[0;0m"
    data.append(["", avgStats[0], round(avgStats[1], 2)])

    final_time = time.time() - start_time

    timeStats['iteration'] += 1
    timeStats['totalNet'] += round((request_time - start_time) * 1000, 0)
    timeStats['totalProgram'] += round((final_time - (request_time - start_time)) * 1000000, 0)

    if round((request_time - start_time) * 1000, 0) > timeStats['maxNet']:
        timeStats['maxNet'] = round((request_time - start_time) * 1000, 0)
    if round((request_time - start_time) * 1000, 0) < timeStats['minNet'] or timeStats['minNet'] == 0:
        timeStats['minNet'] = round((request_time - start_time) * 1000, 0)

    if round((final_time - (request_time - start_time)) * 1000000, 0) > timeStats['maxProgram']:
        timeStats['maxProgram'] = round((final_time - (request_time - start_time)) * 1000000, 0)
    if round((final_time - (request_time - start_time)) * 1000000, 0) < timeStats['minProgram'] or timeStats['minProgram'] == 0:
        timeStats['minProgram'] = round((final_time - (request_time - start_time)) * 1000000, 0)

    timeData = [
        ["time", "current", "average", "min", "max"],
        ["network", round((request_time - start_time) * 1000, 0), timeStats['totalNet'] // timeStats['iteration'], timeStats['minNet'], timeStats['maxNet']],
        ["program", round((final_time - (request_time - start_time)) * 1000000, 0), timeStats['totalProgram'] // timeStats['iteration'], timeStats['minProgram'], timeStats['maxProgram']]
    ]

    timeData[1] = [str(i) + "ms" for i in timeData[1]]
    timeData[1][0] = timeData[1][0][:-2]
    timeData[2] = [str(i) + "us" for i in timeData[2]]
    timeData[2][0] = timeData[2][0][:-2]

    timeTable = tabulate.tabulate(timeData, headers="firstrow", tablefmt="rounded_outline")

    # make table and print
    table = tabulate.tabulate(data, headers=head, tablefmt="rounded_outline", numalign="left")
    os.system('clear')
    print(table)
    print(timeTable)