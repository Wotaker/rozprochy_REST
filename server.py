import flask
import requests
from threading import Thread, Lock
import pandas as pd
import numpy as np
import io
import json


app = flask.Flask(__name__)


threads_results = {
    "country_from_full": None,
    "country_to_full": None,
    "currency_from": None,
    "currency_to": None,
    "latest_rates": None,
    "history": None,
    "error": None
}

err_response = requests.models.Response()

err_lock = Lock()


def thread_country_code(country_name, results_key, results):
    """
    This thread asks https://restcountries.com for translation between country and currency code
    """

    response_from = requests.get(f'https://restcountries.com/v3.1/name/{country_name}')

    if response_from.status_code != requests.codes.ok:
        print(f"Unable to resolve {country_name} currency code")
        with err_lock:
            threads_results['error'] = {
                'code': 511,
                'name': "Translation Error",
                'description': f"Unable to resolve {country_name} country from service at: https://restcountries.com"
            }        
        return
    
    data = response_from.json()
    results[f'currency_{results_key}'] = list(data[0]["currencies"].keys())[0]
    results[f'country_{results_key}_full'] = data[0]["name"]['official']
    return


def thread_latest(results):
    """
    This thread asks https://exchangerate.host/ for latest currency rates
    """

    response = requests.get(f'https://api.exchangerate.host/latest?base={results["currency_from"]}&symbols=USD,EUR,GBP,CHF,BTC,{results["currency_to"]}')
    if response.status_code != requests.codes.ok:
        print("Unable to collect latest currency rates")
        with err_lock:
            threads_results['error'] = {
                'code': 512,
                'name': "Latest Rates Error",
                'description': f"Unable to collect latest currency rates from: https://exchangerate.host/"
            }
        return
    data = response.json()
    results['latest_rates'] = data["rates"]
    return


def thread_history(results, start, end):
    response = requests.get(f'https://api.exchangerate.host/timeseries?start_date={start}&end_date={end}&base={results["currency_from"]}&symbols={results["currency_to"]}&format=csv')
    if response.status_code != requests.codes.ok:
        print("Unable to collect time series currency data")
        with err_lock:
            threads_results['error'] = {
                'code': 513,
                'name': "Time-Series Collection Error",
                'description': f"Unable to collect time series currency data. Start date: {start}, end date: {end}, transition: {results['currency_from']}->{results['currency_to']}." \
                    + f'Service https://api.exchangerate.host/timeseries?start_date={start}&end_date={end}&base={results["currency_from"]}&symbols={results["currency_to"]}&format=csv has failed'
            }
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

    # Assume Error free comunication
    threads_results['error'] = None

    # Parse arguments from URL
    country_from = flask.request.args.get('country_from')
    country_to = flask.request.args.get('country_to')
    start_date = flask.request.args.get('start_date')
    end_date = flask.request.args.get('end_date')
    try:
        amount = int(flask.request.args.get('amount'))
    except ValueError:
        threads_results['error'] = {
            'code': 514,
            'name': "Value Error",
            'description': f"Given amount {flask.request.args.get('amount')} is not an integer"
        }
        return threads_results['error'], threads_results['error']['code']
    amount = amount if amount else 1

    # Create threads to collect data from REST services
    th_country_from = Thread(target=thread_country_code, args=(country_from, "from", threads_results))
    th_country_to = Thread(target=thread_country_code, args=(country_to, "to", threads_results))
    th_latest = Thread(target=thread_latest, args=(threads_results,))
    th_history = Thread(target=thread_history, args=(threads_results, start_date, end_date))

    # Manage threads asynchoniously
        # threads that convert country to currency code can run simultaniously
    th_country_from.start()
    th_country_to.start()

        # Before we run thread latest and thread history, we need to have data from earlier threads
    th_country_from.join()
    th_country_to.join()
        # Error check
    if threads_results['error']:
        return threads_results['error'], threads_results['error']['code']
        
    th_history.start()
    th_latest.start()

        # Now we can join the rest of the threads
    th_latest.join()
    th_history.join()
        # Another Error check
    if threads_results['error']:
        return threads_results['error'], threads_results['error']['code']

    # Calculate the amount of money in foreign currency
    latest_rate = threads_results['latest_rates'][threads_results['currency_to']]
    best_rate = threads_results['history']['best']
    foreign_amount = amount * latest_rate
    foreign_best_amount = amount * best_rate
    loss_ratio = latest_rate / best_rate

    # Create return json dictionary
    json_dict = {
        "args": {
            'country_from': threads_results['country_from_full'],
            'country_to': threads_results['country_to_full'],
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
