import boto3
import sys, hmac, hashlib, base64

# # Unpack command line arguments
# username, app_client_id, key = sys.argv[1:4]

# # Create message and key bytes
# message, key = (username + app_client_id).encode('utf-8'), key.encode('utf-8')

# # Calculate secret hash
# secret_hash = base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()

# print(f"Secret Hash for user '{username}': {secret_hash}")

def generate_secret_hash(username, app_client_id, key): 
    # Create message and key bytes
    message, key = (username + app_client_id).encode('utf-8'), key.encode('utf-8')

    # Calculate secret hash
    secret_hash = base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()

    print(f"Secret Hash for user '{username}': {secret_hash}")

    return secret_hash


# cognito client 초기화
# cognito_client = boto3.client('cognito-idp', region_name='us-west-2')

# response = cognito_client.initiate_auth(
#     ClientId='1v0nu6i734so16207o2mhc0o97',
#     AuthFlow='USER_PASSWORD_AUTH',
#     AuthParameters={
#         'USERNAME': 'haein',
#         'PASSWORD': 'Rkfaorl69*.*',
#         'SECRET_HASH': 'W9sb/Q9NVZ0C4eOKC6iVkwKl90LHT+/wfC2WWiBUeQU='
#     }
# )

# print(response)
