import boto3
import sys
from botocore.exceptions import ParamValidationError
from datetime import datetime 
from tqdm import tqdm
from botocore.config import Config
from botocore.exceptions import ClientError

## Usage Notes: 
### variables need from the users:
#### CapacityReservationID -- The ID of the Capacity Reservation that you want to modify
#### InstanceCount (integer) -- The number of instances for which to reserve capacity. The number of instances can't be increased or decreased by more than 1000 in a single request.
#### EndDateType (String)-- Indicates the way in which the Capacity Reservation ends. A Capacity Reservation can have one of the following end types:
####unlimited - The Capacity Reservation remains active until you explicitly cancel it. Do not provide an EndDate if the EndDateType is unlimited .
####limited - The Capacity Reservation expires automatically at a specified date and time. You must provide an EndDate value if the EndDateType value is limited .
#### For setting ODCR for limited periond, EndDateType = limited
### EndDate (datetime) -- The date and time at which the Capacity Reservation expires. When a Capacity Reservation expires, the reserved capacity is released and you can no longer launch instances into it. The Capacity Reservation's state changes to expired when it reaches its end date and time.
#### You must provide an EndDate value if EndDateType is limited . Omit EndDate if EndDateType is unlimited .
#### If the EndDateType is limited , the Capacity Reservation is cancelled within an hour from the specified time. For example, if you specify 5/31/2019, 13:30:55, the Capacity Reservation is guaranteed to end between 13:30:55 and 14:30:55 on 5/31/2019.
### Ensure you've appropriate permission to Describe instances and reserve capacity

odcr = boto3.client('ec2')

# datetime object containing current date and time
now = datetime.now()

# mm/dd/YY H:M:S
CurrentDate = now.strftime("%m/%d/%Y %H:%M:%S")
print("Curent Date =", CurrentDate)

#### EC2 - modify capacity_reservation
#### if EndDateType is unlimited. Do not provide EndDate
### You must provide three parameters while executing the modifyODCR.py file
#### modifyODCR.py CapacityReservationId InstanceCount EndDateType. Note: EndDate is in the standard UTC time
#### Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'unlimited'

### You must provide four parameters while executing the modifyODCR.py file
#### modifyODCR.py CapacityReservationId InstanceCount EndDateType EndDate. Note: EndDate is in the standard UTC time
#### Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited' '09/25/2021 14:30:00'


if len(sys.argv) <= 4:
    if sys.argv[3] == 'unlimited':
        EndDateType =sys.argv[3]
        CapacityReservationId = sys.argv[1]
        if CapacityReservationId.split('-')[0] !='cr':
            print ("Command to run code to modify to unlimited ODCR is - modifyODCR.py CapacityReservationId InstanceCount EndDateType. Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited'" )
            print ("Note: CapacityReservationId starts with 'cr-'." )
            sys.exit()
        InstanceCount = sys.argv[2]
        #Modify Instances counts
        try:
            IC =  int(InstanceCount)  
        except ValueError as err:
            print("Unable to parse InstanceCount as an integer")
            print ("Command to run code to modify to unlimited ODCR is - modifyODCR.py CapacityReservationId InstanceCount EndDateType. Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited'" )
            print ("Ensure the instance count is a number value")
            sys.exit(1)
elif len(sys.argv) == 5:
    #Existing Capacity Reservation ID
    CapacityReservationId = sys.argv[1]
    if CapacityReservationId.split('-')[0] !='cr':
        print ("Command to run code is - modifyODCR.py CapacityReservationId InstanceCount EndDateType EndDate. Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited' '09/25/2021 14:30:00'" )
        print ("Note: CapacityReservationId starts with 'cr-'. EndDate is in the standard UTC time")
        sys.exit()
    InstanceCount = sys.argv[2]
    #Modify Instances counts
    try:
        IC =  int(InstanceCount)  
    except ValueError as err:
        print("Unable to parse InstanceCount as an integer")
        print ("Command to run code is - modifyODCR.py CapacityReservationId InstanceCount EndDateType EndDate. Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited' '09/25/2021 14:30:00'" )
        print ("Ensure the instance count is a number value")
        sys.exit(1)
    # Ensure EndDateType as 'limited'
    EndDateType = sys.argv[3]
    # End Date for the On-Demand Capacity Reservation
    EndDate = sys.argv[4]
    # Exit program if EndDateType is not set as 'limited'
    if EndDateType != 'limited':
        print ("Command to run code to modify limited ODCR is - modifyODCR.py CapacityReservationId InstanceCount EndDateType EndDate. Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited' '09/25/2021 14:30:00'" )
        print ("Note: EndDate is in the standard UTC time")
        sys.exit()
    #Exit program if End Data has already passed Current Date
    if CurrentDate > EndDate:
            print ("The specified EndDate has already passed. Specify an EndDate in the future.")
            print ("Note: EndDate is in the standard UTC time")
            sys.exit()
else:
    print ("Command to run code to modify to unlimited ODCR is - modifyODCR.py CapacityReservationId InstanceCount EndDateType. Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited'" )
    print ("Ensure the instance count is a number value")
    print ("Command to run code to modify limited ODCR is - modifyODCR.py CapacityReservationId InstanceCount EndDateType EndDate. Ex: modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited' '09/25/2021 14:30:00'" )
    print ("Note: EndDate is in the standard UTC time")
    sys.exit()


def describeCapacityReservation():
    regions = odcr.describe_regions()
    for region in tqdm(regions['Regions']):
        RegionName = region['RegionName']
        #print (RegionName)
        #print ("Analyzing Region ", RegionName)
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
            #region = (response['CapacityReservations'][0]['CapacityReservationArn']).split(':')[3]
        except ClientError as err:
            if (err.response['Error']['Code'] == 'InvalidCapacityReservationId.NotFound'):
                pass
                #print ("The Provided Capacity Reservation does not belong to ",RegionName)
    region = (response['CapacityReservations'][0]['CapacityReservationArn']).split(':')[3]
    return region 

# This method will allow to Modify exiting ODCR. 
# InstanceCount (integer) -- The number of instances for which to reserve capacity. The number of instances can't be increased or decreased by more than 1000 in a single request.
def modifyODCR(region):
    modify = boto3.client('ec2',region_name=region)
    if EndDateType == 'limited':
        ModifyODCR = modify.modify_capacity_reservation(
                    CapacityReservationId=CapacityReservationId,
                    InstanceCount= int(InstanceCount),
                    EndDate=EndDate,
                    EndDateType=EndDateType,
                    DryRun=False
        )
    else:
        ModifyODCR = modify.modify_capacity_reservation(
                    CapacityReservationId=CapacityReservationId,
                    InstanceCount= int(InstanceCount),
                    EndDateType=EndDateType,
                    DryRun=False
        )
    return ModifyODCR['Return']

def main():
    region = describeCapacityReservation()
    if modifyODCR(region):
        print ("Capacity Modification request succeeds")
    else:
        print ("Capacity Modification request does not succeed")

if __name__ == "__main__":
    main()