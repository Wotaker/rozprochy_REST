import requests
import json

def prettyprint(jsondict):
    print(json.dumps(jsondict, indent=2))

def main():
    url = 'http://127.0.0.1:2137/home?country_from=peru&country_to=vietnam&start_date=2022-01-01&end_date=2022-02-01&amount=200'
    response = requests.get(url)
    prettyprint(response.json())
    print(type(response.json()))

if __name__ == '__main__':
    main()
