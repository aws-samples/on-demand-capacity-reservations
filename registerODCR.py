#This script is intended to simply the creation on ODCR for the running capacity across regions with in an account. 
# Here are some of the assumptions –
# User must provide EndDateType as ‘limited’ and the EndDate in the datetime format as ‘2022-01-31 14:30:00’.
# **Note:** EndDate is in the standard UTC time.
# User must have permissions to EC2 APIs such as describe instances, regions and create, modify and cancel capacity reservation. 


import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import sys
from datetime import datetime 
import pandas as pd
from tqdm import tqdm
import pytz


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
#### Ex: registerODCR.py 'limited' '2022-01-31 14:30:00'
#### if EndDataType is unlimited then registerODCR.py EndDateType.
#### Ex: registerODCR.py 'unlimited'

# datetime object containing current date and time
CurrentDate = datetime.now(pytz.utc)
print ("Current Date = ", CurrentDate)

## if EndDateType is 'unlimited, do not provide an EndDate if the EndDateType is unlimited.
## if EndDateType is 'limited', ensure to provide an EndDate. EndDate is in the standard UTC time
if len(sys.argv) == 1:
    print ("Command to run code for unlimited ODCR is - registerODCR.py EndDateType. Ex: registerODCR.py 'unlimited'.")
    print ("Do not specify EndDate")
    print ("Command to run code for limited ODCR is - registerODCR.py EndDateType EndDate. Ex: registerODCR.py 'limited' '2022-01-31 14:30:00'.")
    sys.exit()
elif len(sys.argv) == 2:
    if sys.argv[1] == 'unlimited':
        EndDateType = sys.argv[1]
    else:
        print ("Command to run code is - registerODCR.py EndDateType. Ex: registerODCR.py 'unlimited'.")
        sys.exit()
elif len(sys.argv) == 3:
    EndDateType = sys.argv[1]
    # End Date for the On-Demand Capacity Reservation
    EndDate = sys.argv[2]
    format = '%Y-%m-%d %H:%M:%S'
    try:
        datetime.strptime(EndDate, format)
    except ValueError:
        print ("End Date format is not correct. The correct format is YYYY-MM-DD HH:MI:SS. Here is the command to run code for limited ODCR is - registerODCR.py EndDateType EndDate. Ex: registerODCR.py 'limited' '2022-01-31 14:30:00' ") 
        sys.exit()

    EndDate_obj = datetime.strptime(EndDate, '%Y-%m-%d %H:%M:%S')
    timezone = pytz.timezone('UTC')
    timezone_date_time_obj = timezone.localize(EndDate_obj)
    print ("End Date = ", timezone_date_time_obj)    
    # Exit program if EndDateType is not set as 'limited'
    if EndDateType != 'limited':
        print ("Command to run code for unlimited ODCR is - registerODCR.py EndDateType. Ex: registerODCR.py 'unlimited'.")
        print ("Do not specify EndDate")
        sys.exit()

    #Exit program if End Data has already passed Current Date
    if CurrentDate > timezone_date_time_obj:
            print ("The specified EndDate has already passed. Specify an EndDate in the future.")
            print ("Note: EndDate is in the standard UTC time")
            sys.exit()
else:
    print ("Command to run code for unlimited ODCR is - registerODCR.py EndDateType. Ex: registerODCR.py 'unlimited'.")
    print ("Do not specify EndDate")
    print ("Command to run code for limited ODCR is - registerODCR.py EndDateType EndDate. Ex: registerODCR.py 'limited' '2022-01-31 14:30:00'.")
    sys.exit()


def listTopic(RegionName):
    TopicArn= []
    try:
        sns = boto3.client('sns',region_name=RegionName)
        while True:
            response = sns.list_topics()
            NextToken = response.get('NextToken')
            if NextToken is None:
                NextToken = '' 
            for res in response['Topics']:
                TopicArn.append(res['TopicArn'])
            if NextToken == '':
                break
        return TopicArn  
    except ClientError as err:
        print (err)

#This method creates SNS topic
def createODCRAlarmTopic(RegionName):
    sns = boto3.client('sns', region_name=RegionName)
    try:
        response = sns.create_topic(
        Name='ODCRAlarmNotificationTopic',
        Attributes={
            'DisplayName': 'ODCRAlarm'
        },
        )
        return response['TopicArn']
    except ClientError as err:
        print(err)


# This method creates alarm for each reservation
def createCWAlarm(CapacityReservationId,RegionName):
    TopicArnList = listTopic(RegionName)
    TopicArn = createODCRAlarmTopic(RegionName)
    if TopicArn not in TopicArnList:
        print ("Subscribe and confirm to the SNS Topic {} if not already".format(TopicArn))
    cw = boto3.client('cloudwatch', region_name=RegionName)
    response = cw.put_metric_alarm(
        AlarmName='ODCRAlarm-'+CapacityReservationId,
        AlarmActions=[
        TopicArn,
        ],
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
    return response

# this method helps to identify platform associated with the instance/image
def describePlatform(InstanceId, client):
    response = client.describe_instances(InstanceIds=[InstanceId])
    Platform = ''.join([a_dict['PlatformDetails'] for a_dict in response['Reservations'][0]['Instances']])
    return Platform

# This method retruns Zonal reserve instance (ZRI) if exists or return null.
# filter list has - Scope --> "Availability Zone" and
# state of the Zonal RI as active.

def describeReserveInstances(client):
    zriList = []
    filterList = [{'Name': 'scope','Values': ['Availability Zone']},{'Name': 'state','Values': ['active']}]

    reserveInstances = client.describe_reserved_instances(
    Filters=filterList
    )
    if reserveInstances['ReservedInstances'] == []:
        zriList.extend(reserveInstances['ReservedInstances'])
    else:
        for zri in reserveInstances['ReservedInstances']:
            zaz = zri['InstanceType']+"|"+zri['AvailabilityZone']+"|"+zri['ProductDescription']+"|"+str(zri['InstanceCount'])
            zriList.append(zaz)
    return zriList 

# Global list variable to keep track of the CRI, InstanceType, AZ, Platform and count
ODCRReservation = []
#Next two methods get records describe_instances across regions in an account 
# Describe Instances can lead to throttling your account, so run it during non-peak hours.
# describeInstances() returns list of instances. Parse and pull -  InstanceType +"|" +AvailabilityZone+"|"+Platform
# Checks - instance does not have Capacity reservation, state of the instance is running, 
# Platform is either Windows or UNIX/LINUX, InstanceLifecycle is None and Tenancy is default.
#The entire describe instances -> create ODCR flow is duplicated in the pagination logic. Maybe we can construct a helper that consumes a nextToken, and simply make that null on the first call?
def instanceNextToken(NextToken,client):
    availableInstanceList = []
    filterlist = [{'Name': 'instance-state-name','Values': ['running']},{'Name': 'tenancy','Values': ['default']}]
    # setting MaxResults to 500, if throttled, please set is lower values.
    instances = client.describe_instances(Filters=filterlist, MaxResults=100, NextToken=NextToken)
    NextToken = instances.get('NextToken')
    if NextToken is None:
        NextToken = '' 
    for reservations in instances['Reservations']:
        for instance in reservations['Instances']:
            InstanceLifecycle = instance.get('InstanceLifecycle')
            CapacityReservationId = instance.get('CapacityReservationId')
            Tenancy = instance['Placement'].get('Tenancy')
            CapacityReservationSpecification = len(instance['CapacityReservationSpecification'])
            if (instance['State']['Name'] == 'running' and InstanceLifecycle is None and CapacityReservationId is None and CapacityReservationSpecification != 0 and Tenancy == 'default' ):
                InstanceId = instance['InstanceId']
                ImageId =instance['ImageId'] 
                Platform = describePlatform(InstanceId, client)
                if Platform is None or Platform =='':
                        print ("No Platform is set for the ImageId {}, instanceId {}".format(ImageId,InstanceId))
                InstanceType = instance['InstanceType']
                AvailabilityZone = instance['Placement']['AvailabilityZone']
                availableInstance = (InstanceType +"|" +AvailabilityZone+"|" +Platform) 
                availableInstanceList.append(availableInstance)      
    return NextToken,availableInstanceList


def describeInstances(client):
    avail = []
    NextToken = ''
    while True:
        NextToken,availableInstanceList = instanceNextToken(NextToken,client)
        if availableInstanceList != []:
            avail.extend(availableInstanceList)
        if NextToken == '':
            break
    return avail


# This method returns aggregated list of instances with similar characteristics -  InstanceType +"|" +AvailabilityZone+"|"+Platform+"|"+Count
#Count = counts instance with similar characteristics like Instance Types, AZ, and Platform
def aggregateInstance(client):
    aggregateInstanceList = []
    availInsList = describeInstances(client)
    my_dict = {i:availInsList.count(i) for i in availInsList}
    for key,value in my_dict.items():
        aggregateInstanceList.append(key+"|"+str(value))
    return (aggregateInstanceList)

# This method  check to see if any zonal instance with the appropriate AZ and platform matches with the aggregated ODCR
# if it finds the match it substracts zonal instance count from the aggregated ODCR and create new list
def odcrReservationWithZRI(ZonalRIList,OdcrList):
    newZonalRIDict = {}
    newOdcrDict = {}
    newOdcrList = []

    for zl in ZonalRIList:
        s = zl.split("|")
        hdr = "|".join(s[:3])
        ctn = int(s[3])
        if hdr in newZonalRIDict.keys():
            newZonalRIDict[hdr] += ctn
        else:
            newZonalRIDict[hdr] = ctn

    for ol in OdcrList:
        s = ol.split("|")
        hdr = "|".join(s[:3])
        ctn = int(s[3])
        if hdr in newOdcrDict.keys():
            newOdcrDict[hdr] += ctn
        else:
            newOdcrDict[hdr] = ctn

    for z, val in newZonalRIDict.items():
        if z in newOdcrDict.keys():
            diff = newOdcrDict.get(z) - val
            newOdcrDict.pop(z)
            newOdcrList.append(z + "|" + str(diff))

    if len(newOdcrDict) > 0:
        for key, val in newOdcrDict.items():
            newOdcrList.append(key + "|" + str(val))
    return newOdcrList


# odcrReservation() method creates On-demand Capacity reservations with the supplied EndDateType and EndDate 
def odcrReservation(client,RegionName):  
    OdcrList=aggregateInstance(client)
    zonalRIList = describeReserveInstances(client)
    OdcrWithZonalList = odcrReservationWithZRI(zonalRIList,OdcrList)
    for ls in OdcrWithZonalList:
        #split a record to parse InstanceType, AZ, Platform, and Count
        InstanceType, AZ, Platform, Count = ls.split('|')
        try:
            if int(Count) != 0:
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
                # Output can be added to XLS sheet if needed for future reference.
                CapacityReservationId = OdcrReservation['CapacityReservation']['CapacityReservationId']
                createCWAlarm(CapacityReservationId,RegionName)
                State =  OdcrReservation['CapacityReservation']['State']  
                ODCRReservation.append(InstanceType)
                ODCRReservation.append(Platform)
                ODCRReservation.append(AZ)
                ODCRReservation.append(Count)
                ODCRReservation.append(CapacityReservationId)
                ODCRReservation.append(State) 
        except ClientError as err:
            # Catching an exception where platform is not support with ODCR
            #print ("Error is ",err.response['Error']['Code'])
            if err.response['Error']['Code'] == 'InvalidParameterValue': 
                print("{} platform is not supported under ODCR".format(Platform))
            elif err.response['Error']['Code'] == 'MissingParameter': 
                print("Platform information is not available. It might be private or inactive or not available anymore. Please check it out")
            else:
                print("Some of the parameters to create Capacity Reservation are not valid.")


# Creating XLS sheet of the Capacity reservation detail. The file name is "ODCR.xlsx"
def createXls(list):
    df = pd.DataFrame()
    time = CurrentDate.strftime("%H%M%S")
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
        print ("Analyzing Region ", RegionName)
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
