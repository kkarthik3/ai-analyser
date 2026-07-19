from fyers_apiv3 import fyersModel
from urllib.parse import urlparse, parse_qs

FYERS_APP_ID="IDHL0651SW-100"
FYERS_SECRET_KEY="OHHOCW7TL4"
FYERS_REDIRECT_URI="http://127.0.0.1:8000/api/v1/auth/callback"

client_id = "YOUR_APP_ID"          # Example: ABCD1234-100
secret_key = "YOUR_SECRET_KEY"
redirect_uri = "YOUR_REDIRECT_URI"

session = fyersModel.SessionModel(
    client_id=FYERS_APP_ID,
    secret_key=FYERS_SECRET_KEY,
    redirect_uri=FYERS_REDIRECT_URI,
    response_type="code",
    grant_type="authorization_code"
)

# print(session.generate_authcode())

url = "http://127.0.0.1:8000/api/v1/auth/callback?s=ok&code=200&auth_code=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJJREhMMDY1MVNXIiwidXVpZCI6IjNmMDY3NDIxNDY5NDQ1ZGY5YzI4MTBiZjAxNGJlZDhjIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IlhLMDMxMTQiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIwZDI3ZGY3OGU2NzE0MGI2M2RmMTc1ZmU1YTM5MjE4YWU1NWMwYmJmNzZjMDgwYTFjZjJkZmI2NCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImF1ZCI6IltcImQ6MVwiLFwiZDoyXCIsXCJ4OjBcIixcIng6MVwiXSIsImV4cCI6MTc4NDM4ODYyMSwiaWF0IjoxNzg0MzU4NjIxLCJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJuYmYiOjE3ODQzNTg2MjEsInN1YiI6ImF1dGhfY29kZSJ9.fwqCOEbz9hoGKZGbMrgnn0foCd0cg_6qrjXnt8BVYDc&state=None"

parsed = urlparse(url)
params = parse_qs(parsed.query)

auth_code = params["auth_code"][0]
print(auth_code)
session.set_token(auth_code)
response = session.generate_token()

from fyers_apiv3.FyersWebsocket import order_ws

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJJREhMMDY1MVNXIiwidXVpZCI6IjNmMDY3NDIxNDY5NDQ1ZGY5YzI4MTBiZjAxNGJlZDhjIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IlhLMDMxMTQiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIwZDI3ZGY3OGU2NzE0MGI2M2RmMTc1ZmU1YTM5MjE4YWU1NWMwYmJmNzZjMDgwYTFjZjJkZmI2NCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImF1ZCI6IltcImQ6MVwiLFwiZDoyXCIsXCJ4OjBcIixcIng6MVwiXSIsImV4cCI6MTc4NDM4ODYyMSwiaWF0IjoxNzg0MzU4NjIxLCJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJuYmYiOjE3ODQzNTg2MjEsInN1YiI6ImF1dGhfY29kZSJ9.fwqCOEbz9hoGKZGbMrgnn0foCd0cg_6qrjXnt8BVYDc"

def on_orders(message):
    order = message.get("orders", {})
    print(f"""
Order ID   : {order.get('id')}
Symbol     : {order.get('symbol')}
Qty        : {order.get('qty')}
Filled Qty : {order.get('filledQty')}
Status     : {order.get('status')}
Side       : {'BUY' if order.get('side') == 1 else 'SELL'}
Price      : {order.get('limitPrice')}
""")

def on_open():
    fyers.subscribe(data_type="OnOrders")
    fyers.keep_running()

fyers = order_ws.FyersOrderSocket(
    access_token=ACCESS_TOKEN,
    write_to_file=False,
    log_path="",
    on_connect=on_open,
    on_orders=on_orders,
    on_error=lambda x: print("Error:", x),
    on_close=lambda x: print("Closed:", x),
)

fyers.connect()