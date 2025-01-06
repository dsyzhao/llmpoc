import datetime
import random

def handler(event, context):
    intent_name = event["sessionState"]["intent"]["name"]
    
    if intent_name == "GetTime":
        return handle_time_intent(event)
    elif intent_name == "FallbackIntent":
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": "FallbackIntent",
                    "state": "Fulfilled"
                }
            },
            "messages": [{
                "contentType": "PlainText",
                "content": "I'm sorry, I didn't understand that. Could you please rephrase your question? You can ask me about the time or weather."
            }]
        }

def handle_time_intent(event):
    current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
    
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": event["sessionState"]["intent"]["name"],
                "state": "Fulfilled"
            }
        },
        "messages": [{
            "contentType": "PlainText",
            "content": f"The current time is {current_time}"
        }]
    }

def handle_weather_intent(event):
    slots = event["sessionState"]["intent"]["slots"]
    city = slots.get("City", {}).get("value", {}).get("interpretedValue") if slots.get("City") else None
    country = slots.get("Country", {}).get("value", {}).get("interpretedValue") if slots.get("Country") else None

    # If we're missing either slot, prompt for it
    if not city:
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "ElicitSlot",
                    "slotToElicit": "City"
                },
                "intent": {
                    "name": "GetWeather",
                    "slots": slots,
                    "state": "InProgress"
                }
            },
            "messages": [{
                "contentType": "PlainText",
                "content": "For which city would you like to know the weather?"
            }]
        }
    
    if not country:
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "ElicitSlot",
                    "slotToElicit": "Country"
                },
                "intent": {
                    "name": "GetWeather",
                    "slots": slots,
                    "state": "InProgress"
                }
            },
            "messages": [{
                "contentType": "PlainText",
                "content": f"In which country is {city} located?"
            }]
        }

    # Generate a random temperature between 0 and 35 degrees Celsius
    temperature = random.randint(0, 35)
    
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": "GetWeather",
                "slots": slots,
                "state": "Fulfilled"
            }
        },
        "messages": [{
            "contentType": "PlainText",
            "content": f"The temperature in {city}, {country} is {temperature}°C"
        }]
    } 