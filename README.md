Customers have asked “should they create On-Demand Capacity Reservations (ODCRs) for their existing instances during the critical events like holiday period or Black Friday or marketing campaigns or others?” Customers who want to ensure any instances that are Stopped/Started during the critical event do not encounter an Insufficient Capacity Error (ICE), then they should be covered by ODCR. AWS has no method of predicting in advance, which instance types may be capacity constrained at a time customer needs them (during a recycle). The AWS recommendation is for the customers to analyze their critical instances and cover those with ODCRs for such critical events.

Adding ODCRs to already running instances does not incur additional charges beyond the price of the already running instance. If instances are shut down, and ODCRs are left in place and not resized or deleted, then instance charges will continue to bill. Here is an overview of ODCR billing: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservations-pricing-billing.html

Note: Customers are responsible for creation and management of ODCRs for running capacity. ODCRs for already running instances will not receive Insufficient Capacity Errors when creating the reservation.

This script is intended to simply the creation on ODCR for the running capacity across regions with in an account.

Save the requirements.txt file in the same directory with other python scripts. You may want to run the requirements.txt file if you don't have appropriate dependency to run the rest of the python scripts. You can run using command- 
    **pip3 install -r requirements.txt**  

**Here are some of the assumptions while running the scripts –**

* If user provides EndDateType as 'unlimited', then do not provide EndDate. 
    *Note: Do not provide EndDate.*

* if user provides EndDateType as ‘limited', then provide EndDate. The EndDate forrmat is '2022-01-31 14:30:00'.
    *Note: EndDate is in the standard UTC time.*

* User must have permissions to EC2 APIs such as describe instances, regions and create, describe, modify and cancel capacity reservation. You can download ODCR_IAM.json.
    
    
**To Register ODCR**

registerODCR.py script does 3 things –

1. Describe instances cross-region for an account describeInstances() returns list of instances. Parse and pull – InstanceType|AvailabilityZone|Platform. It checks for instances that have 
    * No Capacity reservation 
    * State of the instance is running 
    * Platform is UNIX/LINUX
    * Tenancy is default and 
    * InstanceLifecycle is None 
    
    *Note: Describe Instances can/may lead to throttling in your account, so run it during non-peak hours.*

2. Aggregates instances with similar characteristics - InstanceType|AvailabilityZone|Platform|Count. 
**Note**: If you have one or more Zonal Reservation Instances (ZRIs) in an account, the script compares them with the existing instances with similar characteristics - Instance Type, AZ and Platform and don't create ODCR for the ZRIs to avoid incurring unwanted charges. But if there are more running instances than ZRIs, the script creates an ODCR for just the delta.  
4. Finally, 
    a. reserves on-demand capacity reservation 
    b. creates an SNS topic with the topic name - ODCRAlarmNotificationTopic in the region where you are registering ODCR, if not already exists.
    c. creates Cloudwatch alarm for InstanceUtilization using the best practices at https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservation-cw-metrics.html
    
    **Note**: You need to subcribe and confirm to the SNS topic, if not already. The code will display the messsage below - 
    
    **Subscribe and confirm to the SNS Topic arn:aws:sns:us-west-2:895432111111:ODCRAlarmNotificationTopic if not already.**
    
    You will receive an email notifcation when Cloudwatch Alarm State changes with:
    SNS Subject (Assuming CW alarms triggers in US East region) - 
        ALARM: "ODCRAlarm-cr-009969c7abf4daxxx" in US East (N. Virginia)
    SNS Body will have the details 
        - CW Alarm, region, link to view the alarm, alarm details, and State Change Actions


**To run script to register ODCRs**
* If EndDateType is **unlimited**. Do not provide EndDate.
    You must provide one parameters while executing the script

    **registerODCR.py' EndDateType**

    **registerODCR.py' 'unlimited'**

* If EndDateType is **limited**. .
    You must provide two parameters while executing the script

    **registerODCR.py' EndDateType EndDate**

    **registerODCR.py' 'limited' '2022-01-31 14:30:00'**


**To modify ODCRs**
 
If need to modify ODCR to change the instance counts for the existing capacity reservation, then the following parameters are required - 
* CapacityReservationID -- The ID of the Capacity Reservation that you want to modify.
* InstanceCount(integer) -- The number of instances for which to reserve capacity. The number of instances can't be increased or decreased by more than 1000 in a single request. 
* EndDateType (String)-- Indicates the way in which the Capacity Reservation ends. A Capacity Reservation can have one of the following end types: 
    
    * unlimited - The Capacity Reservation remains active until you explicitly cancel it. 
        **Do not provide an EndDate if the EndDateType is unlimited.** 
    * limited - The Capacity Reservation expires automatically at a specified date and time. You must provide an EndDate value if the EndDateType value is limited. 
    
    For setting ODCR for limited period, set EndDateType = limited EndDate (datetime), the date and time at which the Capacity Reservation expires. When a Capacity Reservation expires, the reserved capacity is released and you can no longer launch instances into it. The Capacity Reservation's state changes to expired when it reaches its end date and time. You must provide an EndDate value if EndDateType is limited. 
    
    Omit EndDate if EndDateType is unlimited . If the EndDateType is limited , the Capacity Reservation is cancelled within an hour from the specified time. For example, if you specify '2022-01-31 14:30:00', the Capacity Reservation is guaranteed to end between 13:30:55 and 14:30:55 on 5/31/2019. Ensure you've appropriate permission to Describe instances and reserve and modify capacity

**To run the script to modify reservation**

* If EndDateType is **unlimited**. Do not provide EndDate.
    You must provide three parameters while executing the script
    
    **modifyODCR.py CapacityReservationId InstanceCount EndDateType**

    **modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'unlimited'**

* If EndDateType is **limited**.
    You must provide four parameters while executing the modifyODCR.py file 
    
    **modifyODCR.py CapacityReservationId InstanceCount EndDateType EndDate**

    **modifyODCR.py 'cr-05e6a94b99915xxxx' '1' 'limited' '2022-01-31 14:30:00'**

**To cancel ODCRs** 

If you need to cancel capacity reservation, the following parameter is required -
* CapacityReservationID -- The ID of the Capacity Reservation that you want to modify Ensure you've appropriate permission to cancel capacity reservation. The script will cancle ODCR and its associated alarm from the Cloudwatch.

**To cancel capacity_reservation** 

* You must provide one parameters while executing the script
    
    **cancelODCR.py CapacityReservationId**

    **cancelODCR.py 'cr-05e6a94b99915xxxx'**

