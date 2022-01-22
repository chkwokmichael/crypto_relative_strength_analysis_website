# --------------------------------------------------------------------------------------------------------------------
# Import modules

# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask,render_template,url_for,request,flash,redirect
# Importing data manipulation tools
import pandas as pd
import numpy as np
# Importing API tools
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from io import StringIO
from datetime import datetime
# Importing task schedular
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
# Imoprting email tool
import smtplib, ssl

  
# Initiate variables
last_updated = ""
# API connection
CMC_API_KEYS = "86485ec2-7deb-4e04-a89a-7e45a7c80e04"
quote_list = ['price','percent_change_1h','volume_24h','market_cap']
# SMPT connection
smtp_server = "smtp.gmail.com"
sender_email = "cryptorsanalysis@gmail.com"
password = "Crypto100RS"
# receiver_emails = ["fungchunhei1234+testing@gmail.com","freemankwokchinhung+testing@gmail.com"]
receiver_emails = ["freemankwokchinhung+testing@gmail.com"]

# Functions
def get_latest_price(CMC_API_KEYS, quote_list):
    
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    
    parameters = {
      'start':'1',
      'limit':'100',
      'convert':'USD'
    }
    
    headers = {
      'Accepts': 'application/json',
      'X-CMC_PRO_API_KEY': CMC_API_KEYS
    }

    quote_list = quote_list

    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url,params=parameters)
        data = json.loads(response.text)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)

    print('Updating latest price...')

    data_clean = {token['name']: {k:v for k,v in token['quote']['USD'].items() if k in quote_list} for token in data['data']}

    idx = [token['id'] for token in data['data']]

    df = pd.DataFrame(data_clean).T

    df['id'] = idx

    df.to_csv('price.csv')

    global last_updated

    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Email Notification if BTC price drops by 5% in an hour
    if df.loc['Bitcoin','percent_change_1h'] < -2:
    # if True:
        email_notification(smtp_server,sender_email,password,receiver_emails,df)
    
    return df

def email_notification(smtp_server,sender_email,password,receiver_emails,df):

    global last_updated

    port = 587  # For starttls

    message = """\
    Subject": [Alert] Crypto RS Analysis

    BTC has dropped {0:.2f}% within the past hour.

    Your alert for Crypto Relative Strength Analysis has been triggered. Please visit https://crypto-rs-analysis.herokuapp.com/ for more information.

    Last update: {1}
    --------------------------------------------------------------
    Top performing coins:

    """.format(df.loc['Bitcoin','percent_change_1h'],last_updated)

    s = ""
    for index, (token,values) in enumerate(df.drop('Bitcoin').sort_values('percent_change_1h',ascending=False)[:10].iterrows()):
        s += """
        ---------------
        {}. {}
        Price: ${:.2f}
        % (1h): {:.2f}%
        Volume (24h): ${:.2f}M
        Market Cap: ${:.2f}M
        """.format(index+1,token,values['price'],values['percent_change_1h'],values['volume_24h']/1000000,values['market_cap']/1000000)
    
    message += s

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Try to log in to server and send email
    try:
        # first email
        server = smtplib.SMTP(smtp_server,port)
        server.ehlo() # Can be omitted
        server.starttls(context=context) # Secure the connection
        server.ehlo() # Can be omitted
        # Login
        server.login(sender_email, password)
        # Send email here
        server.sendmail(sender_email, receiver_emails, message)
    except Exception as e:
        # Print any error messages to stdout
        print(e)
    finally:
        server.quit() 


# --------------------------------------------------------------------------------------------------------------------
# Initiaate Flask

# Flask constructor takes the name of 
# current module (__name__) as argument.
app = Flask(__name__, static_url_path='/static')
scheduler = BackgroundScheduler()
scheduler.add_job(func=get_latest_price, trigger="interval", hours=1,
                    args = [CMC_API_KEYS,quote_list])
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# --------------------------------------------------------------------------------------------------------------------
# Interact with HTML

# The route() function of the Flask class is a decorator, 
# which tells the application which URL should call 
# the associated function.
@app.route('/')
def home():
    # get_latest_price(CMC_API_KEYS,quote_list)
    global df
    df = get_latest_price(CMC_API_KEYS,quote_list)
    df_btc = df.loc['Bitcoin',:]
    df.drop('Bitcoin',inplace=True)
    return render_template('home.html',df=df,btc=df_btc,last_updated=last_updated,sorted_by='market_cap')

@app.route('/percent_change_1h')
def sorted_perc_change():
    global df
    df = pd.read_csv('price.csv',index_col=0)
    df_btc = df.loc['Bitcoin',:]
    df.drop('Bitcoin',inplace=True)
    df.sort_values('percent_change_1h',ascending=False,inplace=True)
    return render_template('home.html',df=df,btc=df_btc,last_updated=last_updated,sorted_by='percent_change_1h')

@app.route('/volume')
def sorted_volume():
    global df
    df = pd.read_csv('price.csv',index_col=0)
    df_btc = df.loc['Bitcoin',:]
    df.drop('Bitcoin',inplace=True)
    df.sort_values('volume_24h',ascending=False,inplace=True)
    return render_template('home.html',df=df,btc=df_btc,last_updated=last_updated,sorted_by='volume_24h')


  
# main driver function
if __name__ == '__main__':
  
    # run() method of Flask class runs the application 
    # on the local development server.
    app.run()

    # application.run(debug=True)
    # http_server = WSGIServer(('', 5000), application)
    # http_server.serve_forever()