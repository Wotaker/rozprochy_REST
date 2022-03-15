from os import abort
from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import json


app = Flask(__name__)

# encryption key required by Flask-WTF
app.config['SECRET_KEY'] = 'C2HWGVoMGfNTBsrYQg8EcMrdTimkZfAb'

Bootstrap(app)

# Each class is one form field
class MyForm(FlaskForm):
    country_from = StringField(
        'The country name with currency you want to exchange FROM',
        validators=[DataRequired()],
        default="dupa"
    )
    country_to = StringField(
        'The country name with currency you want to exchange TO',
        validators=[DataRequired()],
        default="usa"
    )
    start_date = StringField(
        'Date in format YYYY-MM-DD since when you want to see stats',
        validators=[DataRequired()],
        default="2022-01-01"
    )
    end_date = StringField(
        'Date in format YYYY-MM-DD untill when you want to see stats',
        validators=[DataRequired()],
        default="2022-02-01"
    )
    amount = StringField(
        'Amount of money to exchange',
        validators=[DataRequired()],
        default="100"
    )
    submit = SubmitField('Submit')


def prettyprint(jsondict):
    print(json.dumps(jsondict, indent=2))


@app.route('/', methods=['GET', 'POST'])
def home():
    my_form = MyForm()
    if my_form.validate_on_submit():

        # collect data from submit
        country_from = my_form.country_from.data
        country_to = my_form.country_to.data
        start_date = my_form.start_date.data
        end_date = my_form.end_date.data
        amount = my_form.amount.data

        # fill the form with blanks
        # my_form.country_from.data = ""
        # my_form.country_to.data = ""
        # my_form.start_date.data = ""
        # my_form.end_date.data = ""
        # my_form.amount.data = ""

        # request server for results
        url = f'http://127.0.0.1:2137/home?country_from={country_from}&country_to={country_to}&start_date={start_date}&end_date={end_date}&amount={amount}'
        response = requests.get(url)
        result = response.json()

        error_code = response.status_code
        # Error check
        if error_code != 200:
            print(f"Error {error_code}!")
            if error_code in {511, 512, 513, 514}:
                return render_template(
                    f'error.html',
                    error=str(error_code),
                    name=result['name'],
                    description=result['description']
                ), error_code
            else:
                abort(error_code)

        data = [
            f"Converting {result['out']['currency_from']} ({result['args']['country_from']}) to {result['out']['currency_to']} ({result['args']['country_to']})",
            f"Statistics from {start_date} till {end_date}:",
            f"mean rate: {round(result['out']['history']['mean'], 5)}",
            f"best rate in provided period: {round(result['out']['history']['best'], 5)} ({result['out']['history']['best_date'][:-13]})",
            "Summary",
            f"With current rate ({result['out']['latest rates'][result['out']['currency_to']]}) {amount} {result['out']['currency_from']} is equal to {round(result['out']['summary']['amount return'], 5)} {result['out']['currency_to']}",
            f"On {result['out']['history']['best_date'][:-13]} the same amount was worth {round(result['out']['summary']['best amount'], 5)} {result['out']['currency_to']}",
            f"Latest Rates",
            f"{result['out']['latest rates']}"
        ]
        return render_template(
            'home.html', form=my_form, 
            msg1=data[0],
            msg2=data[1],
            msg3=data[2],
            msg4=data[3],
            msg5=data[4],
            msg6=data[5],
            msg7=data[6],
            msg8=data[7],
            msg9=data[8]
        )

    return render_template(
        'home.html', form=my_form, 
        msg1="", 
        msg2="", 
        msg3="", 
        msg4="", 
        msg5="", 
        msg6="", 
        msg7="",
        msg8="", 
        msg9=""
    )

app.run(port=2138)

