import json
from PIL import Image
import io
import boto3
from pathlib import Path

def download_from_s3(bucket, key):
    s3 = boto3.client('s3')
    buffer = io.BytesIO()
    s3.download_fileobj(bucket, key, buffer)
    buffer.seek(0)
    return Image.open(buffer)

def upload_to_s3(bucket, key, data, content_type='image/jpeg'):
    s3 = boto3.client('s3')
    if isinstance(data, Image.Image):
        buffer = io.BytesIO()
        data.save(buffer, format='JPEG')
        buffer.seek(0)
        s3.upload_fileobj(buffer, bucket, key)
    else:
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

def exif_handler(event, context):
    """
    EXIF Lambda - Process all images in the event
    """
    print("EXIF Lambda triggered")
    print(f"Event received with {len(event.get('Records', []))} SNS records")

    processed_count = 0
    failed_count = 0

    # iterate over all SNS records
    for sns_record in event.get('Records', []):
        try:
            # extract and parse SNS message
            sns_message = json.loads(sns_record['Sns']['Message'])

            # iterate over all S3 records in the SNS message
            for s3_event in sns_message.get('Records', []):
                try:
                    s3_record = s3_event['s3']
                    bucket_name = s3_record['bucket']['name']
                    object_key = s3_record['object']['key']

                    print(f"Processing: s3://{bucket_name}/{object_key}")

                    # download the image from S3 using the bucket and object key
                    image = download_from_s3(bucket_name, object_key)

                    # initialize a dictionary with basic image metadata
                    exif_data = {
                        'width': image.width,
                        'height': image.height,
                        'format': image.format,  # image format (JPEG, PNG)
                        'mode': image.mode  # color mode (RGB, L for greyscale)
                    }

                    # extract EXIF metadata if available
                    # EXIF data contains camera settings, timestamps, GPS, etc.
                    if hasattr(image, 'getexif'):  # check if it supports EXIF extraction
                        exif = image.getexif()  # get EXIF data
                        if exif:
                            for tag_id, value in exif.items():  # iterate over all EXIF tags
                                try:
                                    # convert tag ID and value to strings and add to metadata dictionary
                                    exif_data[str(tag_id)] = str(value)
                                except Exception as e:
                                    print(f"Error processing tag {tag_id}: {e}")

                    # print full extracted metadata for debugging
                    print(f"Extracted EXIF data: {json.dumps(exif_data, indent=2)}")

                    # output S3 key for the JSON metadata file
                    # strip the file extension from the original image name and place under /processed/exif/
                    filename = Path(object_key).stem
                    output_key = f"processed/exif/{filename}.json"

                    # upload the metadata JSON to S3
                    upload_to_s3(bucket_name, output_key, json.dumps(exif_data, indent=2), 'application/json')

                    # print when it's uploaded
                    print(f"Uploaded to: {output_key}")

                    processed_count += 1

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed to process {object_key}: {str(e)}"
                    print(error_msg)

        except Exception as e:
            print(f"Failed to process SNS record: {str(e)}")
            failed_count += 1

    summary = {
        'statusCode': 200 if failed_count == 0 else 207,  # @note: 207 = multi-status
        'processed': processed_count,
        'failed': failed_count,
    }

    print(f"Processing complete: {processed_count} succeeded, {failed_count} failed")
    return summary
