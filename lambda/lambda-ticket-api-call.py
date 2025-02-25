import json
import boto3
import urllib3
import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session(region_name='us-east-1')
bedrock_client = session.client('bedrock-runtime')

def get_item(userInput: str, items: str):
    """from the provided user request choose the right category for name of the requested service items. 

    :param userInput: transcription
    """

    MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

    # Define your system prompt(s).
    # system = [
    #     {
    #         "text": f"""
    #         From the provided user request choose the right category for name of the requested service items and the quantity of the item. 
            
    #         you should follow below guidelines to find the right categories:
    #         <guidelines>
    #         - first look for exact match
    #         - if no exact match is found then look for semantically similar group
    #         - the output should be a list json object like [{{"item": "your selected category", "quantity": "the quantity asked"}}]. for example if someone asked for one blanket for room 851 at 10 AM tomorrow, the output should be : [{{"item": "Blanket", "quantity": "1"}}]
    #         - only return the selected category in the json object nothing else.
    #         - do not include any preamble in your response.
    #         </guidelines> 
    #             here are the possible options: {items}
    #         """
    #     }
    # ]

    system = [
        {
            "text": f"""
            From the provided user request, choose the correct category for the requested service items and their respective quantities.

            <guidelines>
            - First, look for an exact match.
            - If no exact match is found, look for a semantically similar category.
            - The output **must** be a **valid JSON array** containing objects formatted as follows:
            
            ```json
            [
                {{"item": "selected category", "quantity": "requested quantity"}}
            ]
            ```

            - Ensure the JSON is **properly formatted**, with:
            - No extra text, explanations, or preambles.
            - No additional brackets or newline artifacts.
            - A single JSON array containing only the selected items.
            </guidelines> 
            
            Example Output:
            **User Request:** "I need one blanket and two towels for room 851 at 10 AM tomorrow."  
            **Correct JSON Response:**
            ```json
            [
                {{"item": "Blanket", "quantity": "1"}},
                {{"item": "Bath Towel", "quantity": "1"}},
                {{"item": "Air Conditioner", "quantity": "1"}}
            ]

            Here are the possible category options: {items}
            """
        }
    ]





    logger.info(f"{system = }")

    # Your user prompt
    messages = [
        {"role": "user", "content": [{"text":userInput}]},
    ]

    # Configure the inference parameters.
    inf_params = {"maxTokens": 1000, "topP": 0.9, "temperature": 0.0}

    model_response = bedrock_client.converse(
        modelId=MODEL_ID, messages=messages, system=system, inferenceConfig=inf_params
    )

    print(f"{model_response = }")
    return model_response["output"]["message"]["content"][0]['text']


def call_api_endpoint(ticket_data):
    orderUrl = "http://54.175.83.87:33480/robot/order/create"
    http = urllib3.PoolManager(num_pools=1, headers={'Content-Type': 'application/json'})
    dataJson = json.dumps(ticket_data)
    resp = http.request('POST', orderUrl, body=dataJson, timeout=30, retries=5)
    result = json.loads(resp.data)
    return result

def get_request_ticket_api(item, serviceProfile, quantity, userInput, roomNumber, deliveryTime):
    """Generate payload for the api call

    :param item: item requested if any
    :param quantity: how many items requested if applicable
    :param serviceProfile: list of items and corresponding service type and department and request status
    :param userInput: transcription
    """

    ticket = {
              "ticket": {
                  "requests": [
                      {
                          "roomNumber": roomNumber,
                          "robotVer": "chimeInternal_DRAFT",
                          "createBy": "205154476688",
                          "dept": serviceProfile[item]['Department'],  
                          "service": serviceProfile[item]['Service Type'],  
                          "subCategory": item, 
                          "quantity": quantity,
                          "requestTime": str(datetime.datetime.now(datetime.UTC)),
                          "status": serviceProfile[item]['Bot Action'],  
                          "input": userInput,
                          "callIdFull": "99033d55-e034-4e8e-b6fb-d6b17fc122f6",
                          "callStatus": "answer",
                          "callback": "no",
                          "confirmTime": deliveryTime,
                          "botNumber": "+16782030501"
                      }
                  ]
              }
          }
    logger.info(f"{ticket = }")
    api_response = call_api_endpoint(ticket)
    logger.info(f"{api_response = }")
    return json.dumps(api_response)

def s3_retrieve(hotel_number, bucket_name = 'botconfig205154476688v2'):
    s3_client = boto3.client('s3')
    
    service_info_path = f'{hotel_number}serviceInfo.json'
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=service_info_path)
        data = response['Body'].read().decode('utf-8')
        data = json.loads(data)
        return data
        # available_items = [k for k, v in data.items() if v['Avaliable'] == 'Yes']
        # return available_items
    except Exception as e:
        logger.error(f"Error occurred while retrieving {service_info_path}: {e}")
        return {}

def lambda_handler(event, context):
    logger.info(f"{event = }")
    
    phone_number = event['phoneNumber']
    json_service_info = s3_retrieve(phone_number)
    # available_items = [k for k, v in data.items() if v['Avaliable'] == 'Yes']
    logger.info(f"{json_service_info = }")
    items = json_service_info.keys()

    extracted_items = get_item(event["userInput"], ', '.join(items))
    logger.info(f"{extracted_items = }")
    item_quantity = json.loads(extracted_items)
    logger.info(f"{item_quantity = }")

    for i in range(len(item_quantity)):
        get_request_ticket_api(
            item_quantity[i]['item'], 
            json_service_info, 
            item_quantity[i]['quantity'], 
            event["userInput"], 
            event['roomNumber'], 
            event['confirmTime']
            )
    return True


# APPENDIX
    # # Define your system prompt(s).
    # system = [
    #     {
    #         "text": """from the provided user request choose the right category for name of the requested service items and the quantity of the item. 
            
    #         you should follow below guidelines to find the right categories:
    #         <guidelines>
    #         - first look for exact match
    #         - if no exact match is found then look for semantically similar group
    #         - the output should be a list json object like [{"item": "your selected category", "quantity": "the quantity asked"]. for example if someone asked for one blanket for room 851 at 10 AM tomorrow, the output should be : [{"item": "Blanket", "quantity": "1"}]
    #         - only return the selected category in the json object nothing else.
    #         - do not include any preamble in your response.
    #         </guidelines> 
    #             here are the possible options: Menu, Dish Pick Up, Toilet Handle, Toilet, Thermostat, Temperature Control, Smoke Alarm,
    #             Sliding Door, Sink Stopper, Sink Drain, Sink, Shower Door, Shower Converter, Shower, Safe, Retractable Clothes Drying Line, Plug, Toilet Paper Holder,
    #             Toilet Seat, Toilet Seat Cover, Window, Cleaning Service, Change Beds, Bell Cart, Baggage Storage, Bathroom Refresh, Air Freshener, Water Pressure,
    #             Clogged Toilet, Water Leak, Wall Hook, TV Remote, TV, Tub Drain, Towel Bar, Water Issue, Night Stand Lamp, Night Stand, Water Kettle, Bathroom Door,
    #             Bathroom Light, Bathroom, Bar Sink, Air Conditioner, Wheelchair, Umbrella, Bathtub, Toilet Seat Riser, Space Heater, Rollaway Bed, Power Converter,
    #             Plunger, Makeup Mirror, Bathroom Sink, Bed Frame, Mirror, Fridge, Microwave, Light Switch, Light Bulb, Lamp, Jacuzzi Tub, Heater, Faucet, Bedroom Door,
    #             Door Battery, Door, Curtain Rod, Closet Door, Chromecast, Chair, Complaint, Dirty Item Pick Up, Luggage Rack, Early Departure, Movie Theater, Marina,
    #             Meeting Room, Laundry Room, Ice Machine, Gift Shop, Fitness Center, Document Printing, Connect to TV, Call Another Room, Coffee Shop, Closet, Business Center,
    #             Room Service, Restaurant, Nine One One, Outside Call, Pet Fee, Spa, WiFi Password, Complimentary WiFi, WiFi Connection, Voicemail, Vending Machine, Tennis,
    #             Snack Cost, Party Policy, Smoking Area, Shuttle Service, Sauna Room, Security Deposit, Quiet Hours, Pool, Lunch Service, Evening Reception, Dinner Service,
    #             Luggage Assistance, Room Refresh, Room Charge, Room Change, Previous Request, Plumber, Parking, Lost and Found, Sound issues, Laundry and Dry Cleaning,
    #             Late Check Out, QR Code, Outside Food Delivery, Security, Reservation, Sofa Bed Set Up, Room Smell, Brunch Service, Airport Drop Off, Breakfast Service,
    #             Lounge, Bar, Ballroom, Atm Machine, Airport Pick Up, Address, Transportation, Wake Up Call, Valet Parking, Vacuum Service, Turndown Service, Towel Exchange,
    #             Trash Pick Up, Luggage Scale, Ironing Board, TV Channel Guide, Toiletries, Mouthwash, Mini Bar, Mineral Water, Microwavable Food, Medicine, Makeup Remover Wipe,
    #             Lotion, Laundry Detergent, Ketchup Packet, Hair Spray, Gloves, Floss, First Aid Kit, Feminine Hygiene Products, Face Soap, Nail File, Nail Polish Remover Pad,
    #             Note Pad, Shoe Shine Kit, Swim Diaper, Soap, Snack, Shower Gel, Shower Cap, Shower Amenity, Shaving Cream, Paper Towel, Shampoo, Sewing Kit, Room Amenity,
    #             Q-tips, Ponytail Holder, Pen, Face Mask, Disposable Razor, Deodorant, Champagne, Coffee Supplies, Coffee Pod, Coffee Packet, Coffee Creamer, Regular Coffee,
    #             Cleaning Wipes, Bottled Water, Decaf Coffee, Boiling Water, Bathrobe, Bath Slippers, Band-Aid, Talk To A Person, Hours of Operation, Stir Stick,
    #             Decaf Coffee Packets, Dental Kit, Paper Cups, Cotton Balls, Contact Case, Conditioner, Comb, Styrofoam Cups, Plastic Cups, Cups, Decaf Coffee Pod,
    #             Coffee Cup Lid, Coffee Cups, Tea Bag, Sweetener, Sugar Packet, Hot Chocolate, Syrup, Toothbrush, Iron, Toothpaste, Android Charger, Wine Opener, Waste Basket,
    #             Tv Guide, Trash Bag, Toilet Paper, Tissue Box, Utensils, Shower Curtain, Scotch Tape, Scissors, Room Service Menu, Room Key, Restaurant menu, Playing Cards,
    #             HDMI Cable, Iphone Charger, Ipod Docking Station, Clock Radio, Handicap Seat, Hair Dryer, Extension Cord, Earbuds, Ear Plugs, Coffee Machine, CD DVD Player,
    #             Laptop Charger, Box Fan, Battery, Baby Crib, USB Plug, USB Charger Hub, Phone Charger, Nail Clipper, Mattress Pad, Matches, Set of Towels, Blanket, Bedding,
    #             Bed Spread, Top Sheet, Bed Sheet, Towel, Hand Towel, Duvet, Face Towel, Bath Towel, Bath Mat, Ashtray, Sparkling Water, Vanity Kit, Do Not Disturb Sign,
    #             Dress Hanger, Laundry Price List, Pillow, Laundry Bag, Ice Bucket Liner, Ice Bucket, Glasses, Gargle Glass, Pillowcase, Non-Allergenic Pillowcase, Hanger,
    #             Non-Allergenic Pillow, Foam Pillow, Firm Pillow, Feather Pillow, Satin Hanger, Pants Hanger, WiFi Promotional Code"""
    #     }
    # ]