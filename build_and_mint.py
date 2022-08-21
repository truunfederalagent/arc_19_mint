################################
# Arc 19 Minting Example
# Tru.APE
################################


import requests, hashlib, base64, json
from PIL import Image
from algosdk.v2client import algod
from algosdk import mnemonic
from algosdk.future.transaction import AssetConfigTxn
from algosdk.encoding import encode_address
from cid import make_cid

################################
# Load keys into memory and set 
# params for current NFT
################################
with open('keys.json') as f:
    keys = json.loads(f.read())

DALLY_NUM = 18
PARAMS = {
    'background': 'blue',
    'bow': 'green',
    'fill': 'green',
    'skin': 'white',
    'face': 'orange'
}


################################
# Build Current NFT from layers
################################
TOP_LAYERS = ['skin', 'face', 'bow', 'fill']
current_img = Image.open(f'assets/background/{PARAMS["background"]}.png')
for layer in TOP_LAYERS:
    layer_path = PARAMS[layer]
    layer_img = Image.open(f'assets/{layer}/{layer}-{layer_path}.png')
    current_img.paste(layer_img, (0,0), mask=layer_img)

current_img.save(f'images/dally{DALLY_NUM}.png')


################################
# Upload Image to IPFS
# and get resulting CID
################################
IPFS_UPLOAD_URL = 'https://api.nft.storage/upload'
IPFS_HEADERS = {"Authorization": f'Bearer {keys["IPFS_KEY"]}'}

img_file = open(f'images/dally{DALLY_NUM}.png', 'rb')
img_response = requests.post(IPFS_UPLOAD_URL, 
                        img_file, 
                        headers= IPFS_HEADERS
                        )
img_response_data = img_response.json()
img_cid = img_response_data['value']['cid']
print('Image IPFS CID:', img_cid)



################################
# Create Metadata from info
# and upload to IPFS
################################
img_digest = hashlib.sha256(img_file.read()).digest()
img_integrity_hash = base64.b64encode(img_digest).decode('utf-8')
meta_data = {
    "name": f"DALLY{DALLY_NUM:03d}",
    "description": "Dynamic Dally - Configurable NFT project",
    "standard": "arc3",
    "decimals": 0,
    "image": f"ipfs://{img_cid}",
    "image_mimetype": "image/png",
    "image_integrity": f"sha256-{img_integrity_hash}",
    "properties": PARAMS
}
meta_data_bytes = json.dumps(meta_data).encode('utf-8')
meta_response = requests.post(IPFS_UPLOAD_URL, meta_data_bytes, headers=IPFS_HEADERS)
meta_response_data = meta_response.json()
meta_cid = meta_response_data['value']['cid']
print('Metadata IPFS CID:', meta_cid)


################################
# Get Reserve Address for
# corresponding IPFS CID
################################
ipfs = make_cid(meta_cid)
RESERVE_ADDRESS = encode_address(ipfs.multihash[2:])
print('Reserve Address:', RESERVE_ADDRESS)


################################
# Create, sign, and send 
# Asset Configuration Transaction
################################
PUBLIC_KEY = mnemonic.to_public_key(keys['ACCOUNT_MNEMONIC'])
PRIVATE_KEY = mnemonic.to_private_key(keys['ACCOUNT_MNEMONIC'])

NODE_URL = 'https://node.algoexplorerapi.io'
NODE_HEADERS = {'User-Agent': 'py-algorand-sdk'}
algod_client = algod.AlgodClient(algod_token="", algod_address=NODE_URL, headers=NODE_HEADERS)

trans_params = algod_client.suggested_params()
trans_params.fee = 1000
trans_params.flat_fee = True
asset_name = f'Dally {DALLY_NUM:03d}'
unit_name = f'DALLY{DALLY_NUM:03d}'
url = 'template-ipfs://{ipfscid:1:raw:reserve:sha2-256}#arc3'

txn = AssetConfigTxn(
    sender=PUBLIC_KEY,
    sp=trans_params,
    total=1,
    default_frozen=False,
    unit_name=unit_name,
    asset_name=asset_name, 
    manager=PUBLIC_KEY,
    reserve=RESERVE_ADDRESS,
    freeze=None,
    clawback=None,
    strict_empty_address_check=False,
    url=url,
    decimals=0)

signed_transaction = txn.sign(PRIVATE_KEY)
txid = algod_client.send_transaction(signed_transaction)
print('Transaction ID:', txid)
    

################################
# Wait for confirmation and
# get resulting ASA ID
################################
last_round = algod_client.status().get('last-round')
txinfo = algod_client.pending_transaction_info(txid)
while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
    print("Waiting for confirmation")
    last_round += 1
    algod_client.status_after_block(last_round)
    txinfo = algod_client.pending_transaction_info(txid)

print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
ASA_ID = txinfo['asset-index']
print('Created asset:', ASA_ID)