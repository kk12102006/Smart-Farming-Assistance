from flask import Flask, render_template, request
import requests
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# =========================================================
# SHARED FARM DATA
# =========================================================

farm_data = {

    "location": {},

    "weather": {},

    "crop": {},

    "monitoring": [],

    "yield": {},

    "advisory": {}

}

# =========================================================
# MODULE 8 - DATABASE CONFIGURATION
# =========================================================

DATABASE = "smart_farm.db"


def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS monitoring (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            crop_name TEXT NOT NULL,

            crop_week INTEGER NOT NULL,

            plant_height REAL NOT NULL,

            leaf_condition TEXT NOT NULL,

            plant_problem TEXT,

            notes TEXT,

            image TEXT,

            date TEXT NOT NULL
        )
    """)

    connection.commit()

    connection.close()


# Create database automatically
initialize_database()

# =========================================================
# GLOBAL APPLICATION DATA
# =========================================================

monitoring_records = []

weather_data = {}

farm_location = None


# =========================================================
# APPLICATION SETTINGS
# =========================================================

UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder automatically
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# TEMPORARY STORAGE
#
# This is suitable for our beginner prototype.
#
# Later we can replace this with SQLite/database.
# =========================================================

monitoring_records = []


# =========================================================
# MODULE 1 - FARM LOCATION
# =========================================================

@app.route("/", methods=["GET", "POST"])
def location():

    global farm_location

    if request.method == "POST":

        farm_location = request.form.get("location")

        if farm_location:
            farm_location = farm_location.strip()

        if farm_location:

            farm_data["location"] = {

            "location_name": farm_location,

            "latitude": None,

            "longitude": None
        }
            return render_template(

            "location.html",

            location=farm_location,

            submitted=True

        )

        return render_template(
            "location.html",
            error="Please enter your farm location."
        )

    return render_template(
        "location.html",
        location=farm_location
    )



# =========================================================
# MODULE 2 - WEATHER
# =========================================================

@app.route("/weather", methods=["GET", "POST"])
def weather():

    # =====================================================
    # GET REQUEST
    # =====================================================

    if request.method == "GET":

        return render_template(
            "weather.html"
        )

    # =====================================================
    # GET FARM LOCATION COORDINATES
    # =====================================================

    latitude_input = request.form.get("latitude")
    longitude_input = request.form.get("longitude")

    # =====================================================
    # VALIDATE INPUT
    # =====================================================

    if not latitude_input or not longitude_input:

        return render_template(
            "weather.html",
            error="Please enter latitude and longitude."
        )

    try:

        latitude = float(latitude_input)
        longitude = float(longitude_input)

        # =====================================================
    # SAVE LOCATION FOR OTHER MODULES
    # =====================================================


        farm_data["location"] = {

        "location_name":
            farm_data["location"].get(
                "location_name",
                "Farm"
            ),

        "latitude": latitude,

        "longitude": longitude
    }

    except (ValueError, TypeError):

        return render_template(
            "weather.html",
            error="Please enter valid latitude and longitude."
        )

    # =====================================================
    # CHECK VALID COORDINATE RANGE
    # =====================================================

    if latitude < -90 or latitude > 90:

        return render_template(
            "weather.html",
            error="Latitude must be between -90 and 90."
        )

    if longitude < -180 or longitude > 180:

        return render_template(
            "weather.html",
            error="Longitude must be between -180 and 180."
        )

    # =====================================================
    # OPEN-METEO API
    # =====================================================

    url = "https://api.open-meteo.com/v1/forecast"

    parameters = {

        "latitude": latitude,

        "longitude": longitude,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "rain"
        ),

        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum,"
            "precipitation_probability_max"
        ),

        "forecast_days": 5,

        "timezone": "auto"
    }

    # =====================================================
    # CALL WEATHER API
    # =====================================================

    try:

        response = requests.get(
            url,
            params=parameters,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as e:

        print("Weather API Error:", e)

        return render_template(
            "weather.html",
            error="Unable to connect to weather service."
        )

    # =====================================================
    # CURRENT WEATHER
    # =====================================================

    current = data.get(
        "current",
        {}
    )

    temperature = current.get(
        "temperature_2m"
    )

    humidity = current.get(
        "relative_humidity_2m"
    )

    precipitation = current.get(
        "precipitation"
    )

    rain = current.get(
        "rain"
    )

    # =====================================================
    # DAILY FORECAST
    # =====================================================

    daily = data.get(
        "daily",
        {}
    )

    dates = daily.get(
        "time",
        []
    )

    max_temperature = daily.get(
        "temperature_2m_max",
        []
    )

    min_temperature = daily.get(
        "temperature_2m_min",
        []
    )

    rainfall = daily.get(
        "precipitation_sum",
        []
    )

    rain_probability = daily.get(
        "precipitation_probability_max",
        []
    )

    # =====================================================
    # TOMORROW'S WEATHER
    # =====================================================

    tomorrow_rain_probability = 0

    tomorrow_rainfall = 0

    if len(rain_probability) > 1:

        tomorrow_rain_probability = (
            rain_probability[1] or 0
        )

    if len(rainfall) > 1:

        tomorrow_rainfall = (
            rainfall[1] or 0
        )

    # =====================================================
    # IRRIGATION ADVICE
    # =====================================================

    if tomorrow_rain_probability >= 60:

        irrigation_advice = (
            "Rain is likely tomorrow. "
            "Consider reducing or delaying irrigation."
        )

    elif tomorrow_rainfall >= 5:

        irrigation_advice = (
            "Rainfall is expected tomorrow. "
            "Irrigation may not be necessary."
        )

    else:

        irrigation_advice = (
            "Little rainfall is expected tomorrow. "
            "Irrigation may be required if the soil is dry."
        )

    # =====================================================
    # SAVE WEATHER DATA FOR OTHER MODULES
    # =====================================================    

    farm_data["weather"] = {

    "latitude": latitude,

    "longitude": longitude,

    "temperature": temperature,

    "humidity": humidity,

    "precipitation": precipitation,

    "rain": rain,

    "dates": dates,

    "max_temperature": max_temperature,

    "min_temperature": min_temperature,

    "rainfall": rainfall,

    "rain_probability": rain_probability,

    "tomorrow_rain_probability":
        tomorrow_rain_probability,

    "tomorrow_rainfall":
        tomorrow_rainfall,

    "irrigation_advice":
        irrigation_advice
    }    

    # =====================================================
    # SAVE WEATHER DATA FOR DASHBOARD
    # =====================================================

    weather_data.clear()

    weather_data.update({

        "latitude": latitude,

        "longitude": longitude,

        "temperature": temperature,

        "humidity": humidity,

        "precipitation": precipitation,

        "rain": rain,

        "dates": dates,

        "max_temperature": max_temperature,

        "min_temperature": min_temperature,

        "rainfall": rainfall,

        "rain_probability": rain_probability,

        "tomorrow_rain_probability":
            tomorrow_rain_probability,

        "tomorrow_rainfall":
            tomorrow_rainfall,

        "irrigation_advice":
            irrigation_advice
    })

    # =====================================================
    # DISPLAY WEATHER PAGE
    # =====================================================

    return render_template(

        "weather.html",

        latitude=latitude,

        longitude=longitude,

        temperature=temperature,

        humidity=humidity,

        precipitation=precipitation,

        rain=rain,

        dates=dates,

        max_temperature=max_temperature,

        min_temperature=min_temperature,

        rainfall=rainfall,

        rain_probability=rain_probability,

        tomorrow_rain_probability=
            tomorrow_rain_probability,

        tomorrow_rainfall=
            tomorrow_rainfall,

        irrigation_advice=
            irrigation_advice,

        submitted=True
    )




# =========================================================
# MODULE 3 - SOIL & CROP RECOMMENDATION
# =========================================================

@app.route("/crops", methods=["GET", "POST"])
def crops():

    if request.method == "GET":

        return render_template("crop.html")


    # -----------------------------------------------------
    # Farmer input
    # -----------------------------------------------------

    soil_type = request.form.get("soil_type")

    ph_input = request.form.get("ph")

    irrigation = request.form.get("irrigation")

    farm_area_input = request.form.get("farm_area")

    season = request.form.get("season")


    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if not soil_type:

        return render_template(
            "crop.html",
            error="Please select a soil type."
        )


    if not ph_input:

        return render_template(
            "crop.html",
            error="Please enter the soil pH."
        )


    if not irrigation:

        return render_template(
            "crop.html",
            error="Please select irrigation availability."
        )


    if not farm_area_input:

        return render_template(
            "crop.html",
            error="Please enter the farm area."
        )


    if not season:

        return render_template(
            "crop.html",
            error="Please select a growing season."
        )


    try:

        ph = float(ph_input)

    except ValueError:

        return render_template(
            "crop.html",
            error="Please enter a valid pH value."
        )


    if ph < 0 or ph > 14:

        return render_template(
            "crop.html",
            error="Soil pH must be between 0 and 14."
        )


    try:

        farm_area = float(farm_area_input)

    except ValueError:

        return render_template(
            "crop.html",
            error="Please enter a valid farm area."
        )


    if farm_area <= 0:

        return render_template(
            "crop.html",
            error="Farm area must be greater than zero."
        )


    # =====================================================
    # CROP DATABASE
    # =====================================================

    crops_data = {

        # -------------------------
        # KHARIF
        # -------------------------

        "Rice": {
            "season": "kharif",
            "soil": ["clay", "alluvial"],
            "ph_min": 5.5,
            "ph_max": 7.0,
            "irrigation": ["available"]
        },

        "Maize": {
            "season": "kharif",
            "soil": ["loamy", "alluvial", "red"],
            "ph_min": 5.5,
            "ph_max": 7.5,
            "irrigation": ["available", "rainfed"]
        },

        "Ragi": {
            "season": "kharif",
            "soil": ["red", "loamy"],
            "ph_min": 5.5,
            "ph_max": 7.5,
            "irrigation": ["available", "rainfed"]
        },

        "Groundnut": {
            "season": "kharif",
            "soil": ["red", "sandy", "loamy"],
            "ph_min": 6.0,
            "ph_max": 7.5,
            "irrigation": ["available", "rainfed"]
        },

        "Cotton": {
            "season": "kharif",
            "soil": ["black", "loamy"],
            "ph_min": 5.5,
            "ph_max": 8.0,
            "irrigation": ["available", "rainfed"]
        },

        "Soybean": {
            "season": "kharif",
            "soil": ["black", "loamy"],
            "ph_min": 6.0,
            "ph_max": 7.5,
            "irrigation": ["available", "rainfed"]
        },

        "Pigeon Pea (Tur)": {
            "season": "kharif",
            "soil": ["black", "red", "loamy"],
            "ph_min": 5.5,
            "ph_max": 7.5,
            "irrigation": ["rainfed", "available"]
        },

        "Pearl Millet (Bajra)": {
            "season": "kharif",
            "soil": ["sandy", "red", "loamy"],
            "ph_min": 6.0,
            "ph_max": 7.5,
            "irrigation": ["rainfed", "available"]
        },


        # -------------------------
        # RABI
        # -------------------------

        "Wheat": {
            "season": "rabi",
            "soil": ["loamy", "alluvial"],
            "ph_min": 6.0,
            "ph_max": 7.5,
            "irrigation": ["available"]
        },

        "Chickpea (Gram)": {
            "season": "rabi",
            "soil": ["black", "loamy", "alluvial"],
            "ph_min": 6.0,
            "ph_max": 8.0,
            "irrigation": ["rainfed", "available"]
        },

        "Mustard": {
            "season": "rabi",
            "soil": ["loamy", "alluvial", "sandy"],
            "ph_min": 6.0,
            "ph_max": 7.5,
            "irrigation": ["rainfed", "available"]
        },

        "Barley": {
            "season": "rabi",
            "soil": ["loamy", "alluvial", "sandy"],
            "ph_min": 6.0,
            "ph_max": 8.0,
            "irrigation": ["rainfed", "available"]
        },

        "Lentil": {
            "season": "rabi",
            "soil": ["loamy", "alluvial"],
            "ph_min": 5.5,
            "ph_max": 7.5,
            "irrigation": ["rainfed", "available"]
        },

        "Peas": {
            "season": "rabi",
            "soil": ["loamy", "alluvial"],
            "ph_min": 6.0,
            "ph_max": 7.5,
            "irrigation": ["available"]
        },

        "Safflower": {
            "season": "rabi",
            "soil": ["black", "loamy"],
            "ph_min": 6.0,
            "ph_max": 8.0,
            "irrigation": ["rainfed", "available"]
        },

        "Rabi Sorghum (Jowar)": {
            "season": "rabi",
            "soil": ["black", "loamy", "red"],
            "ph_min": 6.0,
            "ph_max": 8.0,
            "irrigation": ["rainfed", "available"]
        }
    }


    # =====================================================
    # CROP SCORING
    # =====================================================

    crop_scores = []


    for crop_name, crop_info in crops_data.items():

        # Only selected season
        if crop_info["season"] != season.lower():
            continue

        score = 0

        reasons = []


        # Soil
        if soil_type.lower() in crop_info["soil"]:

            score += 3

            reasons.append(
                "Suitable soil type"
            )


        # pH
        if (
            crop_info["ph_min"]
            <= ph
            <= crop_info["ph_max"]
        ):

            score += 3

            reasons.append(
                "Suitable soil pH"
            )


        # Irrigation
        if irrigation.lower() in crop_info["irrigation"]:

            score += 2

            reasons.append(
                "Suitable irrigation condition"
            )


        crop_scores.append({

            "name": crop_name,

            "score": score,

            "reasons": reasons
        })


    # Highest score first

    crop_scores.sort(
        key=lambda crop: crop["score"],
        reverse=True
    )


    recommendations = crop_scores[:5]

    # =====================================================
    # SAVE CROP INFORMATION
    # =====================================================

    selected_crop = None

    if recommendations:

        selected_crop = recommendations[0]["name"]


    farm_data["crop"] = {

    "soil_type": soil_type,

    "ph": ph,

    "irrigation": irrigation,

    "farm_area": farm_area,

    "season": season,

    "recommendations": recommendations,

    "selected_crop": selected_crop
    }

    return render_template(

        "crop.html",

        recommendations=recommendations,

        soil_type=soil_type,

        ph=ph,

        irrigation=irrigation,

        farm_area=farm_area,

        season=season,

        submitted=True
    )


# =========================================================
# MODULE 4 - WEEKLY CROP MONITORING
# =========================================================

@app.route("/monitor", methods=["GET", "POST"])
def monitor():

    if request.method == "GET":

        crop_data = farm_data.get(
        "crop",
        {}
    )

        recommendations = crop_data.get(
        "recommendations",
        []
    )

        return render_template(

        "monitoring.html",

        records=monitoring_records,

        recommendations=recommendations

    )


    # -----------------------------------------------------
    # Get farmer input
    # -----------------------------------------------------

    crop_name = request.form.get("crop_name")

    crop_week = request.form.get("crop_week")

    plant_height = request.form.get("plant_height")

    leaf_condition = request.form.get("leaf_condition")

    plant_problem = request.form.get("plant_problem")

    farmer_notes = request.form.get("farmer_notes")


    # -----------------------------------------------------
    # Validate required fields
    # -----------------------------------------------------

    if not crop_name:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Please enter the crop name."
        )


    if not crop_week:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Please enter the crop week."
        )


    if not plant_height:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Please enter the plant height."
        )


    if not leaf_condition:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Please select the leaf condition."
        )


    # -----------------------------------------------------
    # Convert values
    # -----------------------------------------------------

    try:

        crop_week = int(crop_week)

    except ValueError:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Crop week must be a number."
        )


    try:

        plant_height = float(plant_height)

    except ValueError:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Plant height must be a number."
        )


    # -----------------------------------------------------
    # Validate ranges
    # -----------------------------------------------------

    if crop_week < 1:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Crop week must be at least 1."
        )


    if plant_height < 0:

        return render_template(
            "monitoring.html",
            records=monitoring_records,
            error="Plant height cannot be negative."
        )


    # =====================================================
    # IMAGE UPLOAD
    # =====================================================

    image = request.files.get("plant_image")

    image_filename = None


    if image and image.filename:

        # Keep the original filename for now
        image_filename = image.filename

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            image_filename
        )

        image.save(image_path)

    # =====================================================
    # SIMPLE CROP ANALYSIS
    # =====================================================    


    if leaf_condition == "healthy":

        plant_identification = "Plant appears healthy"

        disease_analysis = "No major visible problem reported"

    elif leaf_condition in ["slightly_yellow", "yellow"]:

        plant_identification = "Plant shows possible stress"

        disease_analysis = (
        "Possible nutrient deficiency or water stress. "
        "Further observation recommended."
        )

    elif leaf_condition in ["dry", "spots"]:

        plant_identification = "Plant shows visible stress"

        disease_analysis = (
        "Possible pest, disease or water-related stress. "
        "Inspect the affected leaves."
        )

    else:

        plant_identification = "Analysis unavailable"

        disease_analysis = "Continue monitoring the crop."

    # =====================================================
    # CREATE MONITORING RECORD
    # =====================================================    

    record = {

    "crop_name": crop_name,

    "week": crop_week,

    "plant_height": plant_height,

    "leaf_condition": leaf_condition,

    "plant_problem": plant_problem,

    "notes": farmer_notes,

    "image": image_filename,

    "plant_identification":
        plant_identification,

    "disease_analysis":
        disease_analysis,

    "date": datetime.now().strftime(
        "%d-%m-%Y %H:%M"
    )
}

    # Add record to temporary storage
    monitoring_records.append(record)

    # =====================================================
    # SAVE MONITORING DATA TO SHARED FARM DATA
    # =====================================================
    
    farm_data["monitoring"].append(record)

    # =====================================================
    # LATEST MONITORING DATA
    # =====================================================
    
    farm_data["latest_monitoring"] = record

    # =====================================================
    # SAVE MONITORING RECORD TO DATABASE
    # =====================================================

    connection = get_db_connection()

    connection.execute("""
        INSERT INTO monitoring
        (
            crop_name,
            crop_week,
            plant_height,
            leaf_condition,
            plant_problem,
            notes,
            image,
            date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (

        crop_name,

        crop_week,

        plant_height,

        leaf_condition,

        plant_problem,

        farmer_notes,

        image_filename,

        record["date"]
    ))

    connection.commit()

    connection.close()


    # =====================================================
    # SIMPLE WEEK-TO-WEEK COMPARISON
    # =====================================================

    growth_message = None


    if len(monitoring_records) >= 2:

        previous_record = monitoring_records[-2]

        previous_height = previous_record[
            "plant_height"
        ]

        current_height = plant_height

        growth = current_height - previous_height


        if growth > 0:

            growth_message = (
                f"Plant height increased by "
                f"{growth:.1f} cm "
                f"since the previous monitoring."
            )

        elif growth == 0:

            growth_message = (
                "Plant height has not changed "
                "since the previous monitoring."
            )

        else:

            growth_message = (
                "Plant height is lower than the "
                "previous record. Please verify "
                "the measurements."
            )


    return render_template(

    "monitoring.html",

    records=monitoring_records,

    recommendations=
        farm_data["crop"].get(
            "recommendations",
            []
        ),

    success=True,

    growth_message=growth_message
)





# =========================================================
# MODULE 5 - YIELD PREDICTION
# =========================================================


@app.route("/yield", methods=["GET", "POST"])
def yield_prediction():

    # =====================================================
    # EXPECTED HEIGHT DATABASE
    # =====================================================

    expected_height_data = {

            "rice": 100,
            "wheat": 90,
            "ragi": 100,
            "maize": 200,
            "groundnut": 50,
            "cotton": 150,
            "soybean": 80,
            "chickpea (gram)": 60,
            "chickpea": 60,
            "mustard": 120,
            "barley": 90,
            "lentil": 40,
            "peas": 60,
            "pigeon pea (tur)": 180,
            "pearl millet (bajra)": 150,
            "safflower": 100,
            "rabi sorghum (jowar)": 150
        }    

    # -----------------------------------------------------
    # GET REQUEST
    # -----------------------------------------------------

    if request.method == "GET":

        crop_data = farm_data.get(
            "crop",{})

        latest_monitoring = farm_data.get(
            "latest_monitoring"
            )

        recommendations = crop_data.get(
            "recommendations",
            []
            )

        crop_name = None

        if recommendations:

            crop_name = recommendations[0].get(
            "name"
            )

        crop_week = None

        plant_height = None

        health_condition = None

        expected_height = None

        if crop_name:

            expected_height = expected_height_data.get(
            crop_name.lower().strip()
            )

        if latest_monitoring:

            crop_week = latest_monitoring.get(
            "week"
            )

            plant_height = latest_monitoring.get(
                "plant_height"
            )

            health_condition = latest_monitoring.get(
            "leaf_condition"
            )

        return render_template(

            "yield.html",

            recommendations=recommendations,

            latest_monitoring=latest_monitoring,

            crop_name=crop_name,

            farm_area=crop_data.get(
            "farm_area"
                ),

            crop_week=crop_week,

            plant_height=plant_height,

            health_condition=health_condition,

            expected_height=expected_height
        )    
        


    # -----------------------------------------------------
    # GET FARMER INPUT
    # -----------------------------------------------------

    crop_data = farm_data.get(
    "crop",{})

    latest_monitoring = farm_data.get(
        "latest_monitoring"
    )
    crop_name = request.form.get(
    "crop_name"
    )

    # =====================================================
    # CROP
    # =====================================================

    if not crop_name:

        crop_name = crop_data.get(
        "selected_crop"
        )


    farm_area_input = request.form.get(
    "farm_area"
    )

    # =====================================================
    # FARM AREA
    # =====================================================

    if not farm_area_input:

        farm_area_input = crop_data.get(
            "farm_area"
         )


# =====================================================
# CROP WEEK
# =====================================================


    crop_week_input = request.form.get(
    "crop_week"
)

    if not crop_week_input and latest_monitoring:

        crop_week_input = latest_monitoring.get(
        "week"
    )  

# =====================================================
# PLANT HEIGHT
# =====================================================

    plant_height_input = request.form.get(
    "plant_height"
)

    if not plant_height_input and latest_monitoring:

        plant_height_input = latest_monitoring.get(
        "plant_height"
    )  

# =====================================================
# HEALTH CONDITION
# =====================================================        

    health_condition = request.form.get(
    "health_condition"
)

    if not health_condition and latest_monitoring:

        health_condition = latest_monitoring.get(
        "leaf_condition"
    )  

# =====================================================
# EXPECTED HEIGHT
# =====================================================

    expected_height_input = request.form.get(
    "expected_height"
)

# If farmer does not enter expected height,
# estimate it from the crop's expected growth.
    if not expected_height_input and crop_name:

        expected_height_data = {

        "rice": 100,
        "wheat": 90,
        "ragi": 100,
        "maize": 200,
        "groundnut": 50,
        "cotton": 150,
        "soybean": 80,
        "chickpea (gram)": 60,
        "chickpea": 60,
        "mustard": 120,
        "barley": 90,
        "lentil": 40,
        "peas": 60,
        "pigeon pea (tur)": 180,
        "pearl millet (bajra)": 150,
        "safflower": 100,
        "rabi sorghum (jowar)": 150
    }

    expected_height_input = expected_height_data.get(
        crop_name.lower().strip()
    )        


    # =====================================================
    # CHECK INPUTS
    # =====================================================

    if not crop_name:

        return render_template(
        "yield.html",
        error="Please select a crop from Module 3."
    )


    if not farm_area_input:

        return render_template(
        "yield.html",
        error="Farm area is not available. "
              "Please complete Module 3."
    )


    if not crop_week_input:

        return render_template(
        "yield.html",
        error="No monitoring record found. "
              "Please complete Module 4 first."
    )


    if not plant_height_input:

        return render_template(
        "yield.html",
        error="Plant height is not available. "
              "Please complete Module 4 first."
    )


    if not expected_height_input:

        return render_template(
        "yield.html",
        error="Please enter the expected plant height."
    )


    if not health_condition:

        return render_template(
        "yield.html",
        error="Crop health information is not available. "
              "Please complete Module 4 first."
    )

    # =====================================================
# CONVERT VALUES
# =====================================================

    try:

        farm_area = float(
        farm_area_input
    )

        crop_week = int(
        crop_week_input
    )

        plant_height = float(
        plant_height_input
    )

        expected_height = float(
        expected_height_input
    )

    except (ValueError, TypeError):

        return render_template(
        "yield.html",
            error="Unable to process the farm data. "
              "Please check the previous modules."
    )


    # =====================================================
    # BASIC VALIDATION
    # =====================================================

    if farm_area <= 0:

        return render_template(
        "yield.html",
        error="Farm area must be greater than zero."
    )


    if crop_week <= 0:

        return render_template(
        "yield.html",
        error="Crop week must be greater than zero."
    )


    if plant_height < 0:

        return render_template(
        "yield.html",
        error="Plant height cannot be negative."
    )


    if expected_height <= 0:

        return render_template(
        "yield.html",
            error="Expected height must be greater than zero."
    )


    # =====================================================
    # CROP BASE YIELD DATABASE
    #
    # Approximate prototype values in tonnes/hectare.
    #
    # These are NOT official agricultural forecasts.
    # They are used only to demonstrate the concept.
    # =====================================================

    crop_yield_data = {

        "rice": {
            "yield": 3.5,
            "harvest_week": 18
        },

        "wheat": {
            "yield": 3.2,
            "harvest_week": 16
        },

        "ragi": {
            "yield": 1.8,
            "harvest_week": 16
        },

        "maize": {
            "yield": 3.5,
            "harvest_week": 15
        },

        "groundnut": {
            "yield": 1.8,
            "harvest_week": 16
        },

        "cotton": {
            "yield": 1.5,
            "harvest_week": 24
        },

        "soybean": {
            "yield": 1.4,
            "harvest_week": 17
        },

        "chickpea": {
            "yield": 1.8,
            "harvest_week": 18
        },

        "chickpea (gram)": {
            "yield": 1.8,
            "harvest_week": 18
        },

        "mustard": {
            "yield": 1.4,
            "harvest_week": 16
        },

        "barley": {
            "yield": 2.5,
            "harvest_week": 16
        },

        "lentil": {
            "yield": 1.2,
            "harvest_week": 16
        },

        "peas": {
            "yield": 2.0,
            "harvest_week": 15
        },

        "pigeon pea (tur)": {
            "yield": 1.2,
            "harvest_week": 24
        },

        "pearl millet (bajra)": {
            "yield": 1.5,
            "harvest_week": 14
        },

        "safflower": {
            "yield": 1.0,
            "harvest_week": 18
        },

        "rabi sorghum (jowar)": {
            "yield": 1.2,
            "harvest_week": 18
        }

    }


    # =====================================================
    # FIND CROP
    # =====================================================

    crop_key = crop_name.lower().strip()


    if crop_key in crop_yield_data:

        crop_data = crop_yield_data[
            crop_key
        ]

    else:

        # Default prototype values

        crop_data = {

            "yield": 1.5,

            "harvest_week": 16

        }


    base_yield_per_hectare = crop_data[
        "yield"
    ]

    harvest_week = crop_data[
        "harvest_week"
    ]


    # =====================================================
    # PLANT GROWTH FACTOR
    # =====================================================

    height_ratio = (
        plant_height /
        expected_height
    )


    # Prevent unrealistic values

    if height_ratio > 1:

        height_ratio = 1

    if height_ratio < 0:

        height_ratio = 0


    # =====================================================
    # HEALTH FACTOR
    # =====================================================
    health_factors = {

    "healthy": 1.00,

    "slightly_yellow": 0.90,

    "yellow": 0.80,

    "dry": 0.70,

    "spots": 0.65

    }


    health_factor = health_factors.get(

        health_condition,

        0.75

    )


    # =====================================================
    # GROWTH FACTOR
    # =====================================================

    # We don't want height alone to completely
    # determine yield.

    growth_factor = (

        0.5 +

        (0.5 * height_ratio)

    )


    # =====================================================
    # ESTIMATE YIELD
    # =====================================================

    estimated_yield_per_hectare = (

        base_yield_per_hectare

        * growth_factor

        * health_factor

    )


    # =====================================================
    # FARM AREA
    #
    # Farmer enters acres.
    #
    # 1 acre = 0.404686 hectare
    # =====================================================

    farm_area_hectare = (

        farm_area * 0.404686

    )


    # =====================================================
    # TOTAL ESTIMATED YIELD
    # =====================================================

    total_yield_tonnes = (

        estimated_yield_per_hectare

        * farm_area_hectare

    )


    # Convert tonnes to kg

    total_yield_kg = (

        total_yield_tonnes * 1000

    )


    # =====================================================
    # YIELD STATUS
    # =====================================================

    if height_ratio >= 0.90:

        growth_status = "Excellent"

    elif height_ratio >= 0.75:

        growth_status = "Good"

    elif height_ratio >= 0.60:

        growth_status = "Moderate"

    else:

        growth_status = "Needs Attention"


    # =====================================================
    # HARVEST ESTIMATION
    # =====================================================

    remaining_weeks = (

        harvest_week -

        crop_week

    )


    if remaining_weeks < 0:

        remaining_weeks = 0


    if remaining_weeks == 0:

        harvest_message = (

            "The crop may be approaching "
            "its expected harvest period."

        )

    elif remaining_weeks == 1:

        harvest_message = (

            "Approximately 1 week remaining "
            "until the expected harvest period."

        )

    else:

        harvest_message = (

            f"Approximately {remaining_weeks} "
            f"weeks remaining until the expected "
            f"harvest period."

        )


    # =====================================================
    # CONFIDENCE
    #
    # Prototype confidence based on amount of
    # information available.
    # =====================================================

    confidence = 50

    if plant_height > 0:

        confidence += 10

    if expected_height > 0:

        confidence += 10

    if health_condition:

        confidence += 10

    if crop_key in crop_yield_data:

        confidence += 10


    if confidence > 90:

        confidence = 90



# =====================================================
# SAVE YIELD RESULT FOR OTHER MODULES
# =====================================================

    farm_data["yield"] = {

    "crop_name": crop_name,

    "farm_area": farm_area,

    "crop_week": crop_week,

    "plant_height": plant_height,

    "expected_height": expected_height,

    "growth_status": growth_status,

    "estimated_yield_per_hectare":
        round(
            estimated_yield_per_hectare,
            2
        ),

    "total_yield_tonnes":
        round(
            total_yield_tonnes,
            2
        ),

    "total_yield_kg":
        round(
            total_yield_kg,
            0
        ),

    "harvest_week": harvest_week,

    "remaining_weeks": remaining_weeks,

    "confidence": confidence

    }    

    # =====================================================
    # RESULT
    # =====================================================

    return render_template(

        "yield.html",

        success=True,

        crop_name=crop_name,

        farm_area=farm_area,

        crop_week=crop_week,

        plant_height=plant_height,

        expected_height=expected_height,

        growth_status=growth_status,

        estimated_yield_per_hectare=round(
            estimated_yield_per_hectare,
            2
        ),

        total_yield_tonnes=round(
            total_yield_tonnes,
            2
        ),

        total_yield_kg=round(
            total_yield_kg,
            0
        ),

        harvest_message=harvest_message,

        harvest_week=harvest_week,

        confidence=confidence

    )  

# =========================================================
# MODULE 6 - FARMER ADVISORY & HARVEST PLANNING
# =========================================================


@app.route("/advisory", methods=["GET", "POST"])
def advisory():

    # -----------------------------------------------------
    # GET REQUEST
    # -----------------------------------------------------

    if request.method == "GET":

        crop_data = farm_data.get(
        "crop",
        {}
        )

        latest_monitoring = farm_data.get(
        "latest_monitoring"
        )

        yield_data = farm_data.get(
        "yield",
        {}
        )

        weather_data = farm_data.get(
        "weather",
        {}
        )

        crop_name = None

        recommendations = crop_data.get(
        "recommendations",
        []
        )

        if recommendations:

            crop_name = recommendations[0].get(
            "name"
            )

        crop_week = None
        health_condition = None
        plant_height = None

        if latest_monitoring:

            crop_week = latest_monitoring.get(
            "week"
            )

            health_condition = latest_monitoring.get(
            "leaf_condition"
            )

            plant_height = latest_monitoring.get(
            "plant_height"
            )

        return render_template(

        "advisory.html",

        crop_name=crop_name,

        farm_area=crop_data.get(
            "farm_area"
        ),

        soil_type=crop_data.get(
            "soil_type"
        ),

        ph=crop_data.get(
            "ph"
        ),

        irrigation=crop_data.get(
            "irrigation"
        ),

        season=crop_data.get(
            "season"
        ),

        crop_week=crop_week,

        plant_height=plant_height,

        health_condition=health_condition,

        estimated_yield_per_hectare=
            yield_data.get(
                "estimated_yield_per_hectare"
            ),

        total_yield_tonnes=
            yield_data.get(
                "total_yield_tonnes"
            ),

        harvest_week=
            yield_data.get(
                "harvest_week"
            ),

        remaining_weeks=
            yield_data.get(
                "remaining_weeks"
            ),

        weather_data=weather_data
    )


    # -----------------------------------------------------
    # GET FARM DATA FROM PREVIOUS MODULES
    # -----------------------------------------------------

    crop_data = farm_data.get(
        "crop",{})

    latest_monitoring = farm_data.get(
    "latest_monitoring")

    yield_data = farm_data.get(
        "yield",{})


    # -----------------------------------------------------
    # CROP
    # -----------------------------------------------------

    crop_name = request.form.get(
        "crop_name")

    if not crop_name:

        crop_name = crop_data.get(
            "selected_crop")


    # -----------------------------------------------------
    # CROP WEEK
    # -----------------------------------------------------

    crop_week_input = request.form.get(
        "crop_week")

    if not crop_week_input and latest_monitoring:

        crop_week_input = latest_monitoring.get(
            "week")


    # -----------------------------------------------------
    # HEALTH CONDITION
    # -----------------------------------------------------

    health_condition = request.form.get(
        "health_condition")

    if not health_condition and latest_monitoring:

        health_condition = latest_monitoring.get(
            "leaf_condition")


    # -----------------------------------------------------
    # RAIN FORECAST
    # -----------------------------------------------------

    rain_forecast_input = request.form.get(
        "rain_forecast")

    # =====================================================
    # GET WEATHER DATA FROM MODULE 2
    # =====================================================

    weather_data = farm_data.get(
        "weather",{})

    if not rain_forecast_input and weather_data:

        tomorrow_probability = weather_data.get(
            "tomorrow_rain_probability"
            )

        tomorrow_rainfall = weather_data.get(
            "tomorrow_rainfall"
        )

        if tomorrow_probability is not None:

            if tomorrow_probability >= 70:

                rain_forecast_input = "heavy"

            elif tomorrow_probability >= 40:

                rain_forecast_input = "moderate"
            elif tomorrow_probability >= 20:
            
                rain_forecast_input = "light"    

            else:

                rain_forecast_input = "none"

    # If weather data is not available
    if not rain_forecast_input:

        return render_template(
            "advisory.html",
            error="Weather information is not available. "
              "Please complete Module 2 first."
                )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not crop_name:

        return render_template(
            "advisory.html",
            error="Please enter the crop name."
        )


    if not crop_week_input:

        return render_template(
            "advisory.html",
            error="Please enter the crop week."
        )


    if not health_condition:

        return render_template(
            "advisory.html",
            error="Please select the crop health."
        )


    if not rain_forecast_input:

        return render_template(
            "advisory.html",
            error="Please select the rainfall condition."
        )


    # -----------------------------------------------------
    # CONVERT WEEK
    # -----------------------------------------------------

    try:

        crop_week = int(
            crop_week_input
        )

    except ValueError:

        return render_template(
            "advisory.html",
            error="Crop week must be a number."
        )


    # =====================================================
    # CROP HARVEST DATABASE
    # =====================================================

    crop_data = {

        "rice": {
            "harvest_week": 18
        },

        "wheat": {
            "harvest_week": 16
        },

        "ragi": {
            "harvest_week": 16
        },

        "maize": {
            "harvest_week": 15
        },

        "groundnut": {
            "harvest_week": 16
        },

        "cotton": {
            "harvest_week": 24
        },

        "soybean": {
            "harvest_week": 17
        },

        "chickpea": {
            "harvest_week": 18
        },

        "chickpea (gram)": {
            "harvest_week": 18
        },

        "mustard": {
            "harvest_week": 16
        },

        "barley": {
            "harvest_week": 16
        },

        "lentil": {
            "harvest_week": 16
        },

        "peas": {
            "harvest_week": 15
        },

        "pigeon pea (tur)": {
            "harvest_week": 24
        },

        "pearl millet (bajra)": {
            "harvest_week": 14
        },

        "safflower": {
            "harvest_week": 18
        },

        "rabi sorghum (jowar)": {
            "harvest_week": 18
        }

    }


    crop_key = crop_name.lower().strip()


    if crop_key in crop_data:

        harvest_week = crop_data[
            crop_key
        ]["harvest_week"]

    else:

        harvest_week = 16


    # =====================================================
    # HARVEST ADVISORY
    # =====================================================

    remaining_weeks = (

        harvest_week -
        crop_week

    )


    if remaining_weeks <= 0:

        harvest_advice = (

            "🌾 The crop may be ready for "
            "harvesting. Check the crop carefully "
            "before harvesting."

        )

        harvest_status = "Ready / Near Harvest"


    elif remaining_weeks <= 2:

        harvest_advice = (

            "🌾 Harvest time is approaching. "
            "Start preparing labour, storage "
            "and transportation arrangements."

        )

        harvest_status = "Harvest Approaching"


    else:

        harvest_advice = (

            f"🌱 The crop may need approximately "
            f"{remaining_weeks} more weeks before "
            f"the expected harvest period."

        )

        harvest_status = "Growing"


    # =====================================================
    # IRRIGATION ADVISORY
    # =====================================================

    if rain_forecast_input == "heavy":

        irrigation_advice = (

            "🌧️ Heavy rain is expected. "
            "Avoid unnecessary irrigation and "
            "ensure proper drainage."

        )

        irrigation_status = "Avoid Irrigation"


    elif rain_forecast_input == "moderate":

        irrigation_advice = (

            "🌦️ Moderate rainfall is expected. "
            "Reduce irrigation and monitor the "
            "soil moisture."

        )

        irrigation_status = "Reduce Irrigation"


    elif rain_forecast_input == "light":

        irrigation_advice = (

            "🌦️ Light rainfall is expected. "
            "Monitor soil moisture and irrigate "
            "only if the soil becomes dry."

        )

        irrigation_status = "Monitor Soil"


    else:

        irrigation_advice = (

            "☀️ Little or no rainfall is expected. "
            "Check soil moisture and provide "
            "irrigation when necessary."

        )

        irrigation_status = "Irrigation May Be Needed"


    # =====================================================
    # HEALTH ADVISORY
    # =====================================================

    if health_condition == "healthy":

        health_advice = (

            "🌱 The crop appears healthy. "
            "Continue regular monitoring."

        )

        health_status = "Healthy"


    elif health_condition == "slightly_unhealthy":

        health_advice = (

            "🟡 Some stress may be present. "
            "Monitor leaves, soil moisture and "
            "possible pest activity."

        )

        health_status = "Needs Monitoring"


    elif health_condition == "moderate":

        health_advice = (

            "🟠 Moderate crop stress detected. "
            "Inspect the plants for pests, disease "
            "and nutrient deficiency."

        )

        health_status = "Attention Required"


    else:

        health_advice = (

            "🔴 The crop appears stressed. "
            "Inspect the affected plants and "
            "consider contacting an agricultural "
            "expert if the problem continues."

        )

        health_status = "High Attention"


    # =====================================================
    # GENERAL FARMER ADVICE
    # =====================================================

    general_advice = [

        "Check soil moisture before irrigation.",

        "Monitor the crop at least once every week.",

        "Remove or isolate severely affected plants "
        "if disease is suspected.",

        "Keep records of crop growth and farm inputs.",

        "Avoid unnecessary pesticide or fertilizer use.",

        "Check local weather conditions before "
        "major farm activities."

    ]


    # =====================================================
    # SAVE ADVISORY DATA TO SHARED FARM DATA
    # =====================================================

    farm_data["advisory"] = {

    "crop_name": crop_name,

    "crop_week": crop_week,

    "harvest_status": harvest_status,

    "harvest_advice": harvest_advice,

    "irrigation_status": irrigation_status,

    "irrigation_advice": irrigation_advice,

    "health_status": health_status,

    "health_advice": health_advice,

    "general_advice": general_advice
    }


    # =====================================================
    # RETURN ADVISORY RESULT
    # =====================================================

    return render_template(

    "advisory.html",

    success=True,

    crop_name=crop_name,

    crop_week=crop_week,

    harvest_status=harvest_status,

    harvest_advice=harvest_advice,

    irrigation_status=irrigation_status,

    irrigation_advice=irrigation_advice,

    health_status=health_status,

    health_advice=health_advice,

    general_advice=general_advice

    )
# =========================================================
# MODULE 7 - INTEGRATED FARM DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # =====================================================
    # GET DATA FROM ALL MODULES
    # =====================================================

    crop_data = farm_data.get(
        "crop",{}
    )

    latest_monitoring = farm_data.get(
        "latest_monitoring")

    yield_data = farm_data.get(
        "yield",{}
        )

    advisory_data = farm_data.get(
        "advisory",{}
        )

    # =====================================================
    # ADVISORY DATA FROM MODULE 6
    # =====================================================

    harvest_advice = advisory_data.get(
        "harvest_advice"
        )

    irrigation_advice_module6 = advisory_data.get(
        "irrigation_advice"
        )

    health_advice = advisory_data.get(
        "health_advice"
        )

    general_advice = advisory_data.get(
        "general_advice",
        []
        )


    # ===================================================== 
    # BASIC DEFAULT VALUES
    # =====================================================

    crop_name = crop_data.get(
        "selected_crop"
    )

    crop_week = None

    plant_height = None

    health_condition = None

    plant_identification = None

    disease_analysis = None

    growth_message = None

    # =====================================================
    # GET LATEST MONITORING RECORD
    # =====================================================

    if latest_monitoring:

        crop_week = latest_monitoring.get(
            "week"
            )

        plant_height = latest_monitoring.get(
            "plant_height"
            )

        health_condition = latest_monitoring.get(
            "leaf_condition"
            )

        plant_identification = latest_monitoring.get(
            "plant_identification"
            )

        disease_analysis = latest_monitoring.get(
            "disease_analysis"
            )

        # Use monitoring crop only if
        # Module 3 has not provided one.
        if not crop_name:

            crop_name = latest_monitoring.get(
                "crop_name"
                )

    # =====================================================
    # CROP HEALTH STATUS
    # =====================================================

    if health_condition == "healthy":

        health_status = "Healthy"

        health_icon = "🟢"

        health_message = (
            "The crop appears to be healthy. "
            "Continue regular monitoring."
        )

    elif health_condition in [
        "slightly_yellow",
        "yellow"
    ]:

        health_status = "Needs Monitoring"

        health_icon = "🟡"

        health_message = (
            "Some signs of crop stress are visible. "
            "Monitor soil moisture and leaves."
        )

    elif health_condition in [
        "dry",
        "spots"
    ]:

        health_status = "Attention Required"

        health_icon = "🔴"

        health_message = (
            "The crop may be experiencing stress. "
            "Inspect the plant carefully."
        )

    else:

        health_status = "Not Available"

        health_icon = "⚪"

        health_message = (
            "Upload a weekly plant image to "
            "monitor crop health."
        )

    # =====================================================
    # WEATHER INFORMATION
    # =====================================================

    temperature = weather_data.get(
        "temperature"
    )

    humidity = weather_data.get(
        "humidity"
    )

    rain_probability = weather_data.get(
        "tomorrow_rain_probability"
    )

    tomorrow_rainfall = weather_data.get(
        "tomorrow_rainfall"
    )

    # =====================================================
    # IRRIGATION ADVISORY
    # =====================================================

    if rain_probability is None:

        irrigation_status = "Weather Unavailable"

        irrigation_advice = (
            "Open the Weather module to "
            "get irrigation advice."
        )

    elif rain_probability >= 60:

        irrigation_status = "Reduce Irrigation"

        irrigation_advice = (
            "🌧️ Rain is likely tomorrow. "
            "Consider reducing or delaying irrigation."
        )

    elif tomorrow_rainfall is not None and tomorrow_rainfall >= 5:

        irrigation_status = "Monitor Soil"

        irrigation_advice = (
            "🌦️ Rainfall is expected tomorrow. "
            "Check soil moisture before irrigation."
        )

    else:

        irrigation_status = "Irrigation May Be Needed"

        irrigation_advice = (
            "☀️ Little rainfall is expected. "
            "Check soil moisture and irrigate "
            "if necessary."
        )

    # =====================================================
    # HARVEST & YIELD DATA FROM MODULE 5
    # =====================================================

    harvest_week = yield_data.get(
        "harvest_week"
        )

    remaining_weeks = yield_data.get(
        "remaining_weeks"
        )

    estimated_yield_per_hectare = yield_data.get(
        "estimated_yield_per_hectare"
        )

    total_yield_tonnes = yield_data.get(
        "total_yield_tonnes"
        )

    total_yield_kg = yield_data.get(
        "total_yield_kg"
        )

    yield_confidence = yield_data.get(
        "confidence"
        )

    # =====================================================
    # HARVEST STATUS
    # =====================================================

    if remaining_weeks is None:

        harvest_status = (
            "Monitoring Required"
        )

    elif remaining_weeks == 0:

        harvest_status = (
            "Near Harvest"
        )

    elif remaining_weeks <= 2:

        harvest_status = (
            "Harvest Approaching"
        )

    else:

        harvest_status = (
            "Crop Growing"
        )

    # =====================================================
    # GROWTH MESSAGE
    # =====================================================

    if len(monitoring_records) >= 2:

        previous_record = monitoring_records[-2]

        previous_height = previous_record.get(
            "plant_height",
            0
        )

        current_height = plant_height or 0

        growth = (
            current_height -
            previous_height
        )

        if growth > 0:

            growth_message = (
                f"Plant height increased by "
                f"{growth:.1f} cm since the "
                f"previous monitoring."
            )

        elif growth == 0:

            growth_message = (
                "Plant height has not changed "
                "since the previous monitoring."
            )

        else:

            growth_message = (
                "Plant height is lower than the "
                "previous record. Verify the "
                "measurements."
            )

    # =====================================================
    # AUTOMATIC ACTION PLAN
    # =====================================================

    action_plan = []

    # Health recommendation

    if health_condition in [
        "dry",
        "spots"
    ]:

        action_plan.append(
            "🔍 Inspect the crop for pests "
            "or disease."
        )

    elif health_condition in [
        "slightly_yellow",
        "yellow"
    ]:

        action_plan.append(
            "🌱 Monitor leaves and check "
            "soil moisture."
        )

    else:

        action_plan.append(
            "🌱 Continue weekly crop monitoring."
        )

    # Weather recommendation

    if rain_probability is not None:

        if rain_probability >= 60:

            action_plan.append(
                "🌧️ Rain is likely. Avoid "
                "unnecessary irrigation."
            )

        else:

            action_plan.append(
                "💧 Check soil moisture before "
                "irrigating."
            )

    else:

        action_plan.append(
            "🌦️ Check the weather before "
            "irrigation."
        )

    # Monitoring recommendation

    action_plan.append(
        "📷 Upload a plant image every week "
        "to track crop changes."
    )

    # Harvest recommendation

    if remaining_weeks is not None:

        if remaining_weeks <= 2:

            action_plan.append(
                "🌾 Start preparing for harvest."
            )

        else:

            action_plan.append(
                "📅 Continue monitoring until "
                "the expected harvest period."
            )

    # =====================================================
    # OVERALL FARM STATUS
    # =====================================================

    if health_status == "Attention Required":

        overall_status = "Attention Required"

        overall_icon = "🔴"

    elif health_status == "Needs Monitoring":

        overall_status = "Needs Monitoring"

        overall_icon = "🟡"

    elif health_status == "Healthy":

        overall_status = "Farm Looking Good"

        overall_icon = "🟢"

    else:

        overall_status = "Start Monitoring"

        overall_icon = "🔵"

    # =====================================================
    # RENDER DASHBOARD
    # =====================================================

    return render_template(

        "dashboard.html",

        farm_location=farm_location,

        crop_name=crop_name,

        crop_week=crop_week,

        plant_height=plant_height,

        health_status=health_status,

        health_icon=health_icon,

        health_message=health_message,

        plant_identification=
            plant_identification,

        disease_analysis=
            disease_analysis,

        temperature=temperature,

        humidity=humidity,

        rain_probability=
            rain_probability,

        tomorrow_rainfall=
            tomorrow_rainfall,

        irrigation_status=
            irrigation_status,

        irrigation_advice=
            irrigation_advice,

        growth_message=
            growth_message,

        harvest_status=
            harvest_status,

        harvest_week=
            harvest_week,

        remaining_weeks=
            remaining_weeks,
          

        # =====================================================
        # YIELD INFORMATION FROM MODULE 5
        # =====================================================

        estimated_yield_per_hectare=
            estimated_yield_per_hectare,

        total_yield_tonnes=
            total_yield_tonnes,

        total_yield_kg=
            total_yield_kg,

        yield_confidence=
            yield_confidence,

        action_plan=action_plan,

        # =====================================================
        # MODULE 6 ADVISORY DATA
        # =====================================================

        harvest_advice=harvest_advice,

        irrigation_advice_module6=irrigation_advice_module6,

        health_advice=health_advice,

        general_advice=general_advice,

        overall_status=overall_status,

        overall_icon=overall_icon
    )
# =========================================================
# MODULE 8 - FARM HISTORY
# =========================================================

@app.route("/history")
def history():

    connection = get_db_connection()

    records = connection.execute("""
        SELECT *
        FROM monitoring
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "history.html",
        records=records
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)

