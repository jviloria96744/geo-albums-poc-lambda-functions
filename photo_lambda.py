import json
import os
import uuid
import base64
from io import BytesIO
import boto3
from PIL import Image
import exifread
import requests


s3 = boto3.client("s3")
bucket = os.environ["BUCKET_NAME"]

rekognition = boto3.client("rekognition")

dynamodb = boto3.resource('dynamodb', 'us-west-2')
table = dynamodb.Table(os.environ["TABLE_NAME"])


def upload_photo_to_db(username, photo):
    result = table.update_item(
        Key={
            'username': username,
        },
        UpdateExpression="SET photos = list_append(photos, :i)",
        ExpressionAttributeValues={
            ':i': [photo],
        },
        ReturnValues="UPDATED_NEW"
    )
    if result['ResponseMetadata']['HTTPStatusCode'] == 200 and 'Attributes' in result:
        return True


def lat_lng_calculator(lat_lng, ref, values):
    decimal = sum([float(values[i].num / values[i].den) / 60 ** i for i in range(3)])

    if (lat_lng == "Lat" and ref == "S") or (lat_lng == "Lng" and ref == "W"):
        decimal = -1 * decimal

    return decimal


def get_exif_data(image, file_name, username):
    
    tags = exifread.process_file(image, details=False)
    # for (k, v) in tags.items():
    #     print("Tag: " + k + ", Value: " + str(v.values))
    

    if "GPS GPSDate" not in tags:
        return None


    geo_dict = {
        "Date": tags["GPS GPSDate"].values[:4],
        "File": f"{username}/original/{file_name}",
        "ThumbnailFileName": f"{username}/small/{file_name}",
        "ImageWidth": str(tags["Image ImageWidth"].values[0]),
        "ImageLength": str(tags["Image ImageLength"].values[0]),
        "GPSLat": str(lat_lng_calculator(
            "Lat", tags["GPS GPSLatitudeRef"].values, tags["GPS GPSLatitude"].values
        )),
        "GPSLng": str(lat_lng_calculator(
            "Lng", tags["GPS GPSLongitudeRef"].values, tags["GPS GPSLongitude"].values
        )),
    }

    return geo_dict


def get_labels(encoded_image):

    bytes_object = {"Bytes": encoded_image}
    labels = rekognition.detect_labels(Image=bytes_object)["Labels"]
    labels = [label["Name"] for label in labels if label["Confidence"] > 90]

    return labels


def get_reverse_geocoding(metadata):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    latlng = f"?latlng={metadata['GPSLat']},{metadata['GPSLng']}"
    api_key = os.environ["API_KEY"]
    key = f"&key={api_key}"
    
    url = "".join((base_url, latlng, key))
    
    response = requests.get(url)
    data = response.json()["results"][0]["address_components"]
    country = [item["short_name"] for item in data if "country" in item["types"]]
    cities = [item["long_name"] for item in data if "locality" in item["types"]]
    metadata["City"] = cities
    metadata["Country"] = country


def resize_image(image):
    print(type(image))
    #print("Setting image back to be reread")
    #image.seek(0)
    
    print("Opening image to be resized")
    with Image.open(image) as resized_image:
        print("Resizing image to be 1/3 of original width and height")
        resized_image = resized_image.resize(
            (int(resized_image.width / 3), int(resized_image.height / 3))
        )
    
    return convert_image_to_bytes(resized_image)
    
    
def convert_image_to_bytes(image):
    buf = BytesIO()
    image.save(buf, format='JPEG')
    return buf.getvalue()
    

def process_b64_string(image_string):
    image_string = image_string.split(',', 1)[1]
    image_string = image_string.encode('utf-8')
    return BytesIO(base64.b64decode(image_string))


def lambda_handler(event, context):
    data = json.loads(event['body'])
    username = data["username"]
    file_name = str(uuid.uuid4()) + ".jpg"

    try:
        image = process_b64_string(data["image"])
        metadata = get_exif_data(image, file_name, username)
        if metadata is None:
            raise Exception("This image has no metadata")
            
        get_reverse_geocoding(metadata)
        
        print("Uploading Original Image")
        image = process_b64_string(data["image"])
        s3.upload_fileobj(image, bucket, f"{username}/original/{file_name}")
        print("Original Image Uploaded")
        
        image = process_b64_string(data["image"])
        print("Resizing Image")
        small_image = resize_image(image)
        print("Image Resized")
        print(type(small_image))
        
        metadata['Labels'] = get_labels(small_image)
        s3.put_object(Bucket=bucket, Key=f"{username}/small/{file_name}", Body=small_image)
        
        upload_photo_to_db(username, metadata)
        
        return {
            'statusCode': 200,
            'headers': {"Access-Control-Allow-Origin":"*"},
            'body': json.dumps(metadata)
        }
    except Exception as e:
        return {
            'statusCode': 200,
            'headers': {"Access-Control-Allow-Origin":"*"},
            'body': json.dumps({'Error': 'Error', 'Exception': str(e)})
       }
