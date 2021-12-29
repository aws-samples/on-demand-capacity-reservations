from os import error
import boto3
import sys
from botocore.config import Config
from botocore.exceptions import ParamValidationError
from botocore.exceptions import ClientError
from tqdm import tqdm


## Usage Notes: 
### variables need from the users:
#### CapacityReservationID -- The ID of the Capacity Reservation that you want to cancel
### Ensure you've appropriate permission to cancel capacity reservation
#### EC2 - cancel capacity_reservation
### You must provide one parameters while executing the cancelODCR.py file
#### cancelODCR.py CapacityReservationId 
#### Ex: cancelODCR.py 'cr-05e6a94b99915xxxx'

# Exit program if provided parameters are less than or more than two parameters
if len(sys.argv) != 2:
    print ("Command to run code is here- cancelODCR.py CapacityReservationId Ex: cancelODCR.py 'cr-05e6a94b99915xxxx'" )
    sys.exit()
# Exit program if provided parameters are less than or more than two parameters   
#Existing Capacity Reservation ID
CapacityReservationId = sys.argv[1]
print ("CapacityReservationId=", CapacityReservationId.lstrip())
if CapacityReservationId.split('-')[0] !='cr':
    print ("Command to run code is- cancelODCR.py CapacityReservationId Ex: cancelODCR.py 'cr-05e6a94b99915xxxx'" )
    print ("Note: CapacityReservationId starts with 'cr-'")
    sys.exit()


#Find capacity reservation region
def describeCapacityReservationRegion():
    odcr = boto3.client('ec2')
    regions = odcr.describe_regions()
    for region in tqdm(regions['Regions']):
        RegionName = region['RegionName']
        my_config = Config(
            region_name = RegionName,
            signature_version = 'v4',
            retries = {
                'max_attempts': 10,
                'mode': 'standard'
            }
        )
        client = boto3.client('ec2', config=my_config)
        try: 
            response = client.describe_capacity_reservations(
            CapacityReservationIds=[
                CapacityReservationId,
            ],
            )
            if response['CapacityReservations'][0]['State'] != 'active':
                print ("The state of the Capacity reservation/{} is {}. To cancel Capacity Reservation, please ensure that the state of the Capacity Reservation is active".format(CapacityReservationId, response['CapacityReservations'][0]['State']))
                sys.exit()
        except ParamValidationError as err:
            print ("Invalid Capacity Reservation ID")
            sys.exit()
        except ClientError as err:
            if (err.response['Error']['Code'] == 'InvalidCapacityReservationId.NotFound'):
                pass
            else:
                print ("Command to run code is- cancelODCR.py CapacityReservationId Ex: cancelODCR.py 'cr-05e6a94b99915xxxx'" )
                print ("Note: Ensure Capacity reservation ID is valid and has an accurate format. CapacityReservationId starts with 'cr-'")
                sys.exit()
    region = (response['CapacityReservations'][0]['CapacityReservationArn']).split(':')[3]
    return region        


# Delete alarm for the capacity reservation
def deleteCWAlarm(region):
    try:
        cw = boto3.client('cloudwatch', region_name=region)
        response = cw.delete_alarms(
        AlarmNames=[
            'ODCRAlarm-'+CapacityReservationId,
        ]
        )
    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFound':
            print ("Alarm does not exists")
    except ParamValidationError as err:
        print ("Parameter validation failed error")


# This method will allow to cancel exiting ODCR. 
# CapacityReservationID -- The ID of the Capacity Reservation that you want to cancel
def cancelODCR(region):
    cancel = boto3.client('ec2',region_name=region)
    try:
        CancelODCR = cancel.cancel_capacity_reservation(
        CapacityReservationId=CapacityReservationId,
        DryRun=False
        )
    except ClientError as err:
        print (err.response['Error']['Code'])
    return CancelODCR['Return']


def main():
    region = describeCapacityReservationRegion()
    if cancelODCR(region):
        deleteCWAlarm(region)
        print ("Capacity reservation cancellation request succeeded, and the associated alarm was deleted from the Cloudwatch")
    else:
        print ("Capacity Cancellation request does not succeed")

if __name__ == "__main__":
    main()


