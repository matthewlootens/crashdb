from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from CrashDatabase import CrashDatabase
from CrashSchema import Base, Crash
from sqlalchemy import func
from sqlalchemy.orm import Bundle
from datetime import datetime, time
import json
import decimal
from Config import Config

CONFIG_FILE = 'settings.cfg'
config = Config(CONFIG_FILE).get_config_settings()
DATABASE_FILE = '%s:%s' % (config['mysql']['username'], config['mysql']['password'])
DATABASE_FILE += '@localhost:3306/crash'
app = Flask(__name__)
CORS(app)

########
#Helper Functions and Classes
########
def start_db_session(database_name):
    db = CrashDatabase(database_name, sql_flavor = 'mysql+pymysql')
    return db.new_session()

def get_display_fields():
    """
    Return a list of string names of the columns to aggregate
    """
    # 'number_of_persons_injured', 'number_of_persons_killed',
    display_fields = ['number_of_pedestrians_injured', 'number_of_pedestrians_killed',
                'number_of_cyclist_injured', 'number_of_cyclist_killed',
                'number_of_motorist_injured', 'number_of_motorist_killed']
    return display_fields

def parse_HTML_query(query_dictionary, allowed_keys = ('zip_code', 'borough', 'year')):
    """
    cleans a HTML query of empty values and confirms keys are 'allowed'
    query_dictionary: a dictionary, usually provided by flask's request.args
    values are strings.

    returns the dictionary cleared of keys with an empty value, and
    Need to add error checking for the values and for SQLinjections
        * check for valid types and lengths
        * add a zero for zip_codes
    """
    cleaned_dictionary = {}

    for key, value in query_dictionary.items():
        if key not in allowed_keys:
            continue
        else:
            if value != '':
                cleaned_dictionary[key] = value
    return cleaned_dictionary

def generate_column_bundle(field_list, schema, bundle_name, SQL_function = None):
    """
    helper function to generate a SQLAlchemy column bundle to ease passing many
    field names and generating a heiarchical JSON
    field_list: a simple list of strings containing of the names of columns
    schema: the schema class
    SQL_function: an aggregating function object from SQLAlchemy 'func' library.
    Returns a SQLAlchemy Bundle object for ease of passing to SQLAlchemy queries

    Adds a label element if a SQL_function has been passed in
    """
    try:
        instrumentalized_field_list = [getattr(schema, field) for field in field_list]
    except AttributeError:
        # need a better way to handle the error
        print("Failed to generate a instrumentalized field list. Perhaps a\
        field is not in the class schema definition")

    if SQL_function is None:
        return Bundle(bundle_name, *instrumentalized_field_list)
    else:
        #This adds a label to the function for clarity and ease to make a JSON
        function_list = [SQL_function(field).label(SQL_function().name + '_' + field.name)
                        for field in instrumentalized_field_list]
        return Bundle(bundle_name, *function_list)

#########
#Jsonify Functions
#########
class SQLJSON (json.JSONEncoder):
    """
    Extends the built-in Python JSON encoder to handle
    python's decimal.Decimal values, which SQL natively returns
    """
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            #Probably need to do some kind of testing,
            #lest this cast mess something up;
            #though if this is coming from a decimal in SQL,
            #it would seem okay cast it here
            return float(obj.to_eng_string())
        return json.JSONEncoder.default(self, obj)

def as_dict(SQLAlchemy_result):
    """
    Pass in any result object from SQLAlchemy
    Returns a Python dictionary based on labels and the provided _asdict method
    attribute of these attributes.
    """
    try:
        SQLAlchemy_result._asdict()
    except AttributeError:
        return SQLAlchemy_result

    dictionary = SQLAlchemy_result._asdict()
    for key in dictionary.keys():
        dictionary[key] = as_dict(dictionary[key])
    return dictionary

########
# Routes
########
@app.route("/test")
def confirm_server_status():
    """
    Route to confirm server is running
    """
    return "The server is running."

@app.route("/map")
def get_list():
    """
    Returns a list of JSONs of lat/lng for plotting on google maps
    request.args should contain: lat1, lng1, lat2, lng2
    and also a query term zip boolean
    """
    coords = request.args

    # an optional flag to filter data that does not have a zip code
    show_only_non_zip = request.args['zip']

    # builds a query object and then filters results based on rectangle
    # formed by two lat/long points.
    query = session.query(Crash.unique_key, Crash.latitude, Crash.longitude)
    query = query.filter(Crash.latitude > float(coords['lat1'])).filter(Crash.latitude < float(coords['lat2']))
    query = query.filter(Crash.longitude > float(coords['lng1'])).filter(Crash.latitude > float(coords['lng2']))

    # if the zipcode flag was set to True
    # include only crashes without a zip code
    if show_only_non_zip == 'True':
        query = query.filter(Crash.zip_code < 1)

    # convert SQLAlchemy object to Python dict and then to JSON
    results_list = [as_dict(result) for result in query.all()]
    return json.dumps(results_list, cls = SQLJSON)

@app.route("/crashes")
def queryDatabase():
    """
    Handles requests for crash numbers and can take three query terms:
        borough: a string in all caps, e.g., "BRONX"
        zip_code: a five digit zip, e.g., 10469
        year: a four digit year, e.g., 2016
    """
    try:
        HTML_query_search_terms = parse_HTML_query(request.args)
    except:
        return 'There was an error handleing the HTML query string. Please \
        check that the query keys/values match the avaiable search criteria.'

    display_fields = get_display_fields()
    sum_bundle = generate_column_bundle(display_fields, Crash, 'crash_totals', func.sum)
    query = session.query(Crash.zip_code, sum_bundle)
    query = query.filter_by(**HTML_query_search_terms)
    query = query.group_by(Crash.zip_code)

    print(HTML_query_search_terms)

    # Debugging logging
    # print(request.args)
    # print(sum_bundle)
    # print(query.first())

    results_list = [as_dict(result) for result in query.all()]
    return json.dumps(results_list, cls = SQLJSON)

@app.route("/years")
def get_years(query_object = None):
    """
    Returns an ordered list of years (as JSONs {"year": 2017})
    """
    year_query = session.query(func.year(Crash.date)).distinct().all()
    return json.dumps([{'year': i[0]} for i in year_query])

session = start_db_session(DATABASE_FILE)
