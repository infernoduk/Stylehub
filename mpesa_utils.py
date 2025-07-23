import requests
from requests.auth import HTTPBasicAuth
import base64
from datetime import datetime
from flask import current_app

def get_mpesa_token():
    """Get M-Pesa API authentication token."""
    consumer_key = current_app.config['MPESA_CONSUMER_KEY']
    consumer_secret = current_app.config['MPESA_CONSUMER_SECRET']
    api_url = f"{current_app.config['MPESA_API_URL']}/oauth/v1/generate?grant_type=client_credentials"
    
    try:
        r = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        r.raise_for_status()
        return r.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error getting M-Pesa token: {e}")
        return None

def initiate_stk_push(phone_number, amount, order_id):
    """Initiate M-Pesa STK Push."""
    token = get_mpesa_token()
    if not token:
        return None
        
    api_url = f"{current_app.config['MPESA_API_URL']}/mpesa/stkpush/v1/processrequest"
    
    shortcode = current_app.config['MPESA_BUSINESS_SHORTCODE']
    passkey = current_app.config['MPESA_PASSKEY']
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode('utf-8')

    # Ensure phone number is in the correct format
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]
        
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",  # Or "CustomerBuyGoodsOnline" for Till Numbers
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": f"https://your-ngrok-url.io/mpesa/callback/{order_id}", # Replace with your ngrok URL
        "AccountReference": "StyleHub Order",
        "TransactionDesc": "Payment for StyleHub order"
    }
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        r = requests.post(api_url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error initiating STK push: {e}")
        return None 