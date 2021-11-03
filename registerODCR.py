#This script is intended to simply the creation on ODCR for the running capacity across regions with in an account. 
# Here are some of the assumptions –
# User must provide EndDateType as ‘limited’ and the EndDate in the datetime format as ‘09/25/2021 14:30:00’.
# **Note:** EndDate is in the standard UTC time.
# User must have permissions to EC2 APIs such as describe instances, regions and create, modify and cancel capacity reservation. 


import boto3
from botocore.config import Config
import sys
from datetime import datetime 
import pandas as pd
from tqdm import tqdm

## Usage Notes: 
### variables need from the users:
#### EndDateType (String)-- Indicates the way in which the Capacity Reservation ends. A Capacity Reservation can have one of the following end types:
####unlimited - The Capacity Reservation remains active until you explicitly cancel it. Do not provide an EndDate if the EndDateType is unlimited .
####limited - The Capacity Reservation expires automatically at a specified date and time. You must provide an EndDate value if the EndDateType value is limited .
#### For setting ODCR for limited perionf, EndDateType = limited
#### EndDate (datetime) -- The date and time at which the Capacity Reservation expires. When a Capacity Reservation expires, the reserved capacity is released and you can no longer launch instances into it. The Capacity Reservation's state changes to expired when it reaches its end date and time.
#### You must provide an EndDate value if EndDateType is limited . Omit EndDate if EndDateType is unlimited .
#### If the EndDateType is limited , the Capacity Reservation is cancelled within an hour from the specified time. For example, if you specify 5/31/2019, 13:30:55, the Capacity Reservation is guaranteed to end between 13:30:55 and 14:30:55 on 5/31/2019.
#### Ensure you've appropriate permission to Describe instances and reserve capacity
#### EC2 - describe instances,regions, and create, modify and cancel capacity_reservation

#### To execute the code
### if EndDataType is limited then registerODCR.py EndDateType EndDate. Note: EndDate is in the standard UTC time
#### Ex: registerODCR.py 'limited' '09/25/2021 14:30:00'
#### if EndDataType is unlimited then registerODCR.py EndDateType.
#### Ex: registerODCR.py 'unlimited'

# datetime object containing current date and time
now = datetime.now()
# mm/dd/YY H:M:S
CurrentDate = now.strftime("%m/%d/%Y %H:%M:%S")
print("Curent Date =", CurrentDate)

## if EndDateType is 'unlimited, do not provide an EndDate if the EndDateType is unlimited.
## if EndDateType is 'limited', ensure to provide an EndDate. EndDate is in the standard UTC time
if len(sys.argv) <= 2:
    if sys.argv[1] == 'unlimited':
        EndDateType = sys.argv[1]
    else:
        print ("Command to run code is - registerODCR.py EndDateType. Ex: registerODCR.py 'unlimited'.")
        sys.exit()
elif len(sys.argv) <= 3:
    EndDateType = sys.argv[1]
    # End Date for the On-Demand Capacity Reservation
    EndDate = sys.argv[2]
    print ("End Date = ", EndDate)
    # Exit program if EndDateType is not set as 'limited'
    if EndDateType != 'limited':
        print ("Command to run code for unlimited ODCR is - registerODCR.py EndDateType. Ex: registerODCR.py 'unlimited'.")
        print ("Do not specify EndDate")
        sys.exit()
    #Exit program if End Data has already passed Current Date
    if CurrentDate > EndDate:
            print ("The specified EndDate has already passed. Specify an EndDate in the future.")
            print ("Note: EndDate is in the standard UTC time")
            sys.exit()
else:
    print ("Command to run code for unlimited ODCR is - registerODCR.py EndDateType. Ex: registerODCR.py 'unlimited'.")
    print ("Do not specify EndDate")
    print ("Command to run code for limited ODCR is - registerODCR.py EndDateType EndDate. Ex: registerODCR.py 'unlimited' '09/25/2021 14:30:00'.")
    sys.exit()

# This method creates alarm for each reservation
def createCWAlarm(CapacityReservationId,RegionName):
    cw = boto3.client('cloudwatch', region_name=RegionName)
    response = cw.put_metric_alarm(
        AlarmName='ODCRAlarm-'+CapacityReservationId,
        MetricName='InstanceUtilization',
        Namespace='AWS/EC2CapacityReservations',
        Statistic='Average',
        Dimensions=[
            {
                'Name': 'CapacityReservationId',
                'Value': CapacityReservationId
            },
        ],
        Period=300,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=50,
        ComparisonOperator='LessThanThreshold',
    )

# Global list variable to keep track of the CRI, InstanceType, AZ, Platform and count
ODCRReservation = []
#Describe_instances in the list -  availableInstanceList 
# Describe Instances can lead to throttling your account, so run it during non-peak hours.
# describeInstances() returns list of instances. Parse and pull -  InstanceType +"|" +AvailabilityZone+"|"+Platform
# Checks - instance does not have Capacity reservation, state of the instance is running, 
# Platform is either Windows or UNIX/LINUX, InstanceLifecycle is None and Tenancy is default.
def describeInstances(client):
    availableInstanceList = []
    filterlist = [{'Name': 'instance-state-name','Values': ['running']}]
    # setting MaxResults to 500, if throttled, please set is lower values.
    instances = client.describe_instances(Filters=filterlist, MaxResults=500)
    for reservations in instances['Reservations']:
        for instance in reservations['Instances']:
            InstanceLifecycle = instance.get('InstanceLifecycle')
            CapacityReservationId = instance.get('CapacityReservationId')
            Platform = instance.get('Platform')
            Tenancy = instance['Placement'].get('Tenancy')
            if Platform is None:
                Platform = 'Linux/UNIX'
            if (instance['State']['Name'] == 'running' and InstanceLifecycle is None and CapacityReservationId is None and Tenancy == 'default' ):
                InstanceType = instance['InstanceType']
                AvailabilityZone = instance['Placement']['AvailabilityZone']
                availableInstance = (InstanceType +"|" +AvailabilityZone+"|" +Platform) 
                availableInstanceList.append(availableInstance)
    while('NextToken' in instances): 
        # setting MaxResults to 500, if throttled, please set is lower values.
        instances = client.describe_instances(Filters=filterlist, MaxResults=500, NextToken=instances['NextToken'])
        for reservations in instances['Reservations']:
            for instance in reservations['Instances']:
                InstanceLifecycle = instance.get('InstanceLifecycle')
                CapacityReservationId = instance.get('CapacityReservationId')
                Platform = instance.get('Platform')
                if Platform is None:
                    Platform = 'Linux/UNIX'
                if (instance['State']['Name'] == 'running' and InstanceLifecycle is None and CapacityReservationId is None ):
                    InstanceType = instance['InstanceType']
                    AvailabilityZone = instance['Placement']['AvailabilityZone'] 
                    availableInstance = (InstanceType +"|" +AvailabilityZone+"|"+Platform) 
                    availableInstanceList.append(availableInstance)
    return availableInstanceList
             
# This method returns aggregated list of instances with similar characteristics -  InstanceType +"|" +AvailabilityZone+"|"+Platform+"|"+Count
#Count = counts instance with similar characteristics like Instance Types, AZ, and Platform
def aggregateInstance(client):
    aggregateInstanceList = []
    availInsList=[]
    availInsList = describeInstances(client)
    temp_list = []
    for ind in availInsList:
        index = availInsList.index(ind)
        temp_list = availInsList[index+1:]
        #count to add instances with similar characteristics
        count = 1
        #xcount to keep track of index to delete elements from the availInsList if elements matches with temp_list.
        xcount = 0
        for x in temp_list:
            if ind != x:
                xcount = xcount+1
            else: 
                count = count+1
                del availInsList[xcount]
        aggInstance = ind + "|" + str(count)
        aggregateInstanceList.append(aggInstance)  
    return aggregateInstanceList

# odcrReservation() method creates On-demand Capacity reservations with the supplied EndDateType and EndDate 
def odcrReservation(client,RegionName):
    OdcrList=[]
    OdcrList=aggregateInstance(client)
    for ls in OdcrList:
        #split a record to parse InstanceType, AZ, Platform, and Count
        InstanceType, AZ, Platform, Count = ls.split('|')
        #State = ''
        # If you plan to test it out then set DryRun=True
        if EndDateType == 'limited':
            OdcrReservation = client.create_capacity_reservation(
                InstanceType=InstanceType,
                InstancePlatform=Platform,
                AvailabilityZone=AZ,
                InstanceCount=int(Count),
                EndDate = EndDate,
                EndDateType = EndDateType,
                DryRun=False)
        else:
            OdcrReservation = client.create_capacity_reservation(
                InstanceType=InstanceType,
                InstancePlatform=Platform,
                AvailabilityZone=AZ,
                InstanceCount=int(Count),
                EndDateType = EndDateType,
                DryRun=False)
        #print (OdcrReservation)
        # Output can be added to XLS sheet if needed for future reference.
        CapacityReservationId = OdcrReservation['CapacityReservation']['CapacityReservationId']
        createCWAlarm(CapacityReservationId,RegionName)
        State =  OdcrReservation['CapacityReservation']['State']  
        #print ("state is ", State) 
        ODCRReservation.append(InstanceType)
        ODCRReservation.append(Platform)
        ODCRReservation.append(AZ)
        ODCRReservation.append(Count)
        ODCRReservation.append(CapacityReservationId)
        ODCRReservation.append(State) 

# Creating XLS sheet of the Capacity reservation detail. The file name is "ODCR.xlsx"
def createXls(list):
    df = pd.DataFrame()
    time = now.strftime("%H%M%S")
    filename = "ODCR"+"-"+time+".xlsx"
    print ("The results are available in  ./" + filename + ".")
    df['InstanceType'] = list[0::6]
    df['AvailabilityZone'] = list[1::6]
    df['InstancePlatform'] = list[2::6]
    df['Count'] = list[3::6]
    df['CapacityReservationId'] = list[4::6]
    df['State'] = list[5::6]
    df.to_excel(filename, index = False)

# Pulling instances cross-region from an account 
# Connecting EC2 service tp desctribe instances
def main():
    client1 = boto3.client('ec2')
    regions = client1.describe_regions()
    for region in tqdm(regions['Regions']):
        RegionName = region['RegionName']
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
        odcrReservation(client,RegionName)
    createXls(ODCRReservation)

if __name__ == "__main__":
    main()


