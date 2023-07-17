import json
import requests

from datetime import datetime
from OdooLocust.OdooLocustUser import OdooLocustUser
from locust import between


class User(OdooLocustUser):
    wait_time = between(5, 15)
    host = "localhost"
    database = "locust_13"
    login = "admin"
    password = "admin"
    port = 8069
    protocol = "jsonrpc"
    abstract = True
    server_address = 'http://localhost:8069'
    user_count = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cookie = False
        self.csrf_token = False
        # Simple uuid for each user so that we can differentiate between them. Using uuid so that we can restart without having to recreate the db
        self.id = User.user_count
        User.user_count += 1
        self.context = {}
        self.today = datetime.today()
        self.onchange_specs = {}

    def on_start(self):
        super().on_start()
        # By getting the session cookie, we can then send post request by using so that the client is authenticated
        # Unfortunately this is not a way to get the csrf token
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": {
                'db': self.database,
                'login': self.login,
                'password': self.password,
                "context": {},
            },
        }
        res = requests.get(f'{self.server_address}/web/session/authenticate', data=json.dumps(payload), headers={
            'Content-Type': 'application/json',
        })
        self.cookie = res.headers.get('set-cookie')
        res = requests.get(
            f'{self.server_address}/web/login',
            headers={'Cookie': self.cookie}
        )
        # Get the value of the input csrf_token from the html login form.
        self.csrf_token = res.content.decode('utf-8').split('csrf_token: "')[1].split('"')[0]
        self.context = {
            "lang": "en_US",
            "tz": "Europe/Brussels",
            "uid": self.client.user_id,
            "allowed_company_ids": [
                1
            ]
        }
