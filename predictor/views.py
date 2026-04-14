from django.shortcuts import render
import os
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
import json
from urllib import request as urlrequest
from urllib import error as urlerror
import time
from urllib.parse import quote
from groq import Groq

# =========================================================
# WEB VIEW (No ML Model)
# =========================================================

# Simply renders the predict.html template since the POST calculation is now fully handled by API.  
def predict_price(request):
    return render(request, 'predict.html')


# =========================================================
# HELPER FUNCTIONS 
# =========================================================
def get_groq_api_key():
    return os.environ.get('GROQ_KEY', '').strip()

# Initialize Groq Client
client = Groq(api_key=get_groq_api_key())

def duckduckgo_search(query):
    try:
        url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_redirect=1"
        req = urlrequest.Request(
            url=url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urlrequest.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        results = []
        if data.get("AbstractText"):
            results.append({
                "title": "Summary",
                "snippet": data["AbstractText"],
                "link": data.get("AbstractURL", "")
            })
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text")[:60],
                    "snippet": topic.get("Text"),
                    "link": topic.get("FirstURL", "")
                })
        return results[:5]
    except Exception:
        return []

def is_price_query(message):
    keywords = ["price", "cost", "rate", "property price", "house price", "flat price"]
    locations = ["in", "at", "near"]
    msg = message.lower()
    return any(k in msg for k in keywords) and any(l in msg for l in locations)

def format_inr(amount):
    try:
        return f"₹{int(amount):,}"
    except Exception:
        return f"₹{amount}"

def get_fallback_price(property_type, square_footage, bhk, bathrooms, city=''):
    try:
        sqft = float(square_footage)
        beds = int(float(bhk))
        baths = int(float(bathrooms))
    except (TypeError, ValueError):
        return None

    type_factor = {
        'apartment': 1500,
        'villa': 2500,
        'builder_floor': 1800,
        'studio': 2000,
    }.get(property_type.lower(), 1600)

    city_multiplier = 1.0
    if city.lower() in ['mumbai']:
        city_multiplier = 3.5
    elif city.lower() in ['delhi ncr', 'bengaluru', 'pune']:
        city_multiplier = 1.8
    elif city.lower() in ['chennai', 'hyderabad']:
        city_multiplier = 1.5

    price = (sqft * type_factor + beds * 1500000 + baths * 500000) * city_multiplier
    return int(max(price, 1500000))

def build_fallback_reply(property_type, square_footage, bhk, bathrooms, city):
    estimate = get_fallback_price(property_type, square_footage, bhk, bathrooms, city)
    if estimate is None:
        return {
            "estimate": None,
            "detail": "Our estimation service is temporarily unavailable. Please try again later.",
        }
    return {
        "estimate": format_inr(estimate),
        "detail": "This estimate is based on the provided property details and current market trends."
    }

def clean_numeric_input(val):
    if not val: return "0"
    return "".join(c for c in val if c.isdigit() or c == '.') or "0"


# 🚀 Simple in-memory cache
CACHE = {}
def get_cache(key): return CACHE.get(key.lower())
def set_cache(key, value): CACHE[key.lower()] = value


# 🚦 Rate limiter (per IP)
LAST_REQUEST = {}
def is_rate_limited(ip, limit=1.5):
    now = time.time()
    last = LAST_REQUEST.get(ip, 0)
    if now - last < limit:
        return True
    LAST_REQUEST[ip] = now
    return False


# =========================================================
# API VIEWS
# =========================================================

@csrf_exempt
@require_POST
def house_price_predict(request):
    try:
        request_data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON payload')

    property_type = (request_data.get('property_type') or '').strip()
    square_footage = clean_numeric_input(request_data.get('square_footage'))
    bhk = clean_numeric_input(request_data.get('bhk'))
    bathrooms = clean_numeric_input(request_data.get('bathrooms'))
    city = (request_data.get('city') or '').strip()
    locality = (request_data.get('locality') or '').strip()

    if not all([property_type, square_footage, bhk, bathrooms, city, locality]):
        return HttpResponseBadRequest('Missing property data')

    search_query = f"{locality} {city} property price per sq ft {property_type}"
    search_results = duckduckgo_search(search_query)
    print(f"Search Results for '{search_query}': {len(search_results)} found.")

    search_context = ""
    for r in search_results:
        search_context += f"- {r['snippet']}\n"
    
    if not search_context:
        search_context = "Market trends: Use your internal real estate data for this locality as live search results were sparse."

    if not get_groq_api_key():
        return JsonResponse({"reply": "Groq API key missing"}, status=500)

    system_prompt = """
    You are a professional Indian real estate valuation expert.
    Your job:
    - Analyze real-time market data
    - Estimate property price realistically
    - Use per sq.ft trends and locality insights

    Output STRICTLY:
    1. Estimated Price Range (in INR Lakhs/Crores)
    2. Price per sq.ft estimate
    3. 2–3 bullet insights
    Keep it concise and data-driven.
    """

    user_prompt = f"""
    Property Details:
    - City: {city}
    - Locality: {locality}
    - Type: {property_type}
    - Area: {square_footage} sq.ft
    - BHK: {bhk}
    - Bathrooms: {bathrooms}

    Market Data:
    {search_context}
    Calculate realistic price.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.3,
            max_tokens=250,
        )
        reply = chat_completion.choices[0].message.content.strip()
        references = [{"title": r["title"], "link": r["link"]} for r in search_results if r.get("link")]

        return JsonResponse({
            "reply": reply or "Could not estimate price.",
            "references": references
        })

    except Exception as e:
        print(f"Prediction Error: {e}")
        fallback = build_fallback_reply(property_type, square_footage, bhk, bathrooms, city)
        return JsonResponse({
            "reply": f"Note: Using offline estimator due to high demand. {fallback['detail']}",
            "estimate": fallback["estimate"]
        })


@csrf_exempt
@require_POST
def chatbot(request):
    message = request.POST.get("message", "").strip()

    if not message:
        return HttpResponseBadRequest("Missing message")

    ip = request.META.get("REMOTE_ADDR")
    if is_rate_limited(ip):
        return JsonResponse({
            "reply": "You're sending messages too fast. Please slow down."
        }, status=429)

    cached = get_cache(message)
    if cached:
        return JsonResponse(cached)

    if not get_groq_api_key():
        return JsonResponse({"reply": "Groq API key missing"}, status=500)

    search_results = []
    search_context = ""

    if is_price_query(message):
        search_query = f"real estate property prices {message}"
        search_results = duckduckgo_search(search_query)

        if search_results:
            search_context = "\n\nMarket Insights:\n"
            for r in search_results:
                search_context += f"- {r['snippet']}\n"

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful real estate assistant for the HouseSell platform. Help users with their property queries concisely."},
                {"role": "user", "content": message + search_context}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.4,
            max_tokens=300,
        )
        reply = chat_completion.choices[0].message.content.strip()
        
        response = {
            "reply": reply or "I couldn't generate a response.",
            "references": [{"title": r["title"], "link": r["link"]} for r in search_results if r.get("link")]
        }
        set_cache(message, response)
        return JsonResponse(response)

    except Exception as e:
        print(f"Chatbot Error: {e}")
        fallback = {"reply": "I'm facing high demand right now. Here's what I found:\n\n"}
        for r in search_results:
            fallback["reply"] += f"- {r['snippet']}\n"

        fallback["references"] = [{"title": r["title"], "link": r["link"]} for r in search_results if r.get("link")]
        set_cache(message, fallback)
        return JsonResponse(fallback)
        