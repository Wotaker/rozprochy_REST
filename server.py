import flask
import requests
from threading import Thread
import pandas as pd
import numpy as np
import io


app = flask.Flask(__name__)


threads_results = {
    "currency_from": None,
    "currency_to": None,
    "latest_rates": None,
    "history": None
}


def thread_country_code(country_name, results_key, results):
    """
    This thread asks https://restcountries.com for translation between country and currency code
    """

    response_from = requests.get(f'https://restcountries.com/v3.1/name/{country_name}')

    if response_from.status_code != requests.codes.ok:
        print(f"Unable to resolve {country_name} currency code")
        return
    
    data = response_from.json()
    results[results_key] = list(data[0]["currencies"].keys())[0]
    return


def thread_latest(results):
    """
    This thread asks https://exchangerate.host/ for latest currency rates
    """

    response = requests.get(f'https://api.exchangerate.host/latest?base={results["currency_from"]}&symbols=USD,EUR,GBP,CHF,BTC,{results["currency_to"]}')
    if response.status_code != requests.codes.ok:
        print("Unable to collect latest currency rates")
        return
    data = response.json()
    results['latest_rates'] = data["rates"]
    return


def thread_history(results, start, end):
    response = requests.get(f'https://api.exchangerate.host/timeseries?start_date={start}&end_date={end}&base={results["currency_from"]}&symbols={results["currency_to"]}&format=csv')
    if response.status_code != requests.codes.ok:
        print("Unable to collect time series currency data")
        return
    
    # load csv into data frame
    df = pd.read_csv(io.StringIO(response.text), decimal=',')
    df['rate'] = pd.to_numeric(df['rate'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])

    # agregate data
    mean = df['rate'].mean()
    best = df['rate'].max()
    best_date = df['date'][df['rate'].argmax()]

    results['history'] = {
        'mean': mean,
        'best': best,
        'best_date': best_date.date()
    }
    return


@app.route('/home', methods=['GET'])
def gettest():

    # Parse arguments from URL
    country_from = flask.request.args.get('country_from')
    country_to = flask.request.args.get('country_to')
    start_date = flask.request.args.get('start_date')
    end_date = flask.request.args.get('end_date')
    amount = int(flask.request.args.get('amount'))
    amount = amount if amount else 1

    # Create threads to collect data from REST services
    th_country_from = Thread(target=thread_country_code, args=(country_from, "currency_from", threads_results))
    th_country_to = Thread(target=thread_country_code, args=(country_to, "currency_to", threads_results))
    th_latest = Thread(target=thread_latest, args=(threads_results,))
    th_history = Thread(target=thread_history, args=(threads_results, start_date, end_date))

    # Manage threads asynchoniously
        # threads that convert country to currency code can run simultaniously
    th_country_from.start()
    th_country_to.start()

        # Before we run thread latest and thread history, we need to have data from earlier threads
    th_country_from.join()
    th_country_to.join()
    th_history.start()
    th_latest.start()

        # Now we can join the rest of the threads
    th_latest.join()
    th_history.join()

    # Calculate the amount of money in foreign currency
    latest_rate = threads_results['latest_rates'][threads_results['currency_to']]
    best_rate = threads_results['history']['best']
    foreign_amount = amount * latest_rate
    foreign_best_amount = amount * best_rate
    loss_ratio = latest_rate / best_rate

    # Create return json dictionary
    json_dict = {
        "args": {
            'country_from': country_from,
            'country_to': country_to,
            'start_date': start_date,
            'end_date': end_date,
            'amount': amount
        },
        "out": {
            'currency_from': threads_results['currency_from'],
            'currency_to': threads_results['currency_to'],
            'latest rates': threads_results['latest_rates'],
            'history': threads_results['history'],
            'summary': {
                "loss ratio": loss_ratio,
                "amount return": foreign_amount,
                "best amount": foreign_best_amount,
                "difference": foreign_best_amount - foreign_amount
            }
        }
    }

    return json_dict

app.run(port=2137)
