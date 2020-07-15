import json
import boto3
import os

dynamodb = boto3.resource('dynamodb', 'us-west-2')
table = dynamodb.Table(os.environ["TABLE_NAME"])
s3 = boto3.client("s3")

def create_login_user(username, password):

    response = table.get_item(Key={"username": username})
    if "Item" in response:
        if response["Item"]["password"] == password:
            for photo in response["Item"]["photos"]:
                photo["GPSLat"] = float(photo["GPSLat"])
                photo["GPSLng"] = float(photo["GPSLng"])
                photo["ImageWidth"] = int(photo["ImageWidth"])
                photo["ImageLength"] = int(photo["ImageLength"])

            return {
                "user": response["Item"],
                "alert": ""
            }
        else:
            return {
                "user": None,
                "alert": "Your username/password doesn't match"
            }
    else:
        entry = {
            "username": username,
            "password": password,
            "photos": []
        }

        table.put_item(Item=entry)
        return {
            "user": entry,
            "alert": ""
        }
        
        
def delete_user(username):
    bucket = os.environ["BUCKET_NAME"]
    response = s3.list_objects_v2(Bucket=bucket, Prefix=username )
    if "Contents" in response:
        key_list = [{"Key": item["Key"]} for item in response["Contents"]]
        s3.delete_objects(Bucket=bucket, Delete={'Objects': key_list})

    table.delete_item(Key={"username": username})

    return {"username": username}

def lambda_handler(event, context):
    
    method = event['httpMethod']
    body = json.loads(event["body"])
    print(body)
    print(method)
    
    if method == 'POST':
    
        username = body['username']
        password = body['password']
    
        user = create_login_user(username, password)
        
    elif method == 'DELETE':
        username = body['username']
        user = delete_user(username)
        
    print(user)
        
    return {
        'statusCode': 200,
        "headers": {"Access-Control-Allow-Origin":"*"},
        'body': json.dumps(user)
    }
