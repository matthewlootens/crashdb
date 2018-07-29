from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from CrashDatabase import CrashDatabase
from CrashSchema import Base, Crash
from sqlalchemy import func
from sqlalchemy.orm import Bundle
from datetime import datetime, time
import json
import decimal
import configparser

with file.open(CONFIG_FILE) as f:
    config = configparser.RawConfigParser()
    config.read_file(f)

# E_FILE = 'root:Light773@localhost:3306/crash'
DATABASE_FILE = config[mysql][username] + 'root:Light773@localhost:3306/crash'
app = Flask(__name__)
CORS(app)
columns = ['zip_code', 'borough']

####Helper Functions and Classes####
def start_db_session(database_name):
    db = CrashDatabase(database_name, sql_flavor = 'mysql+pymysql')
    return db.new_session()

def get_crashes_by_borough(borough_request):
    """
    Returns a query object of crashes in a specified borough
    """
    return session.query(Crash).filter_by(borough = borough_request)

def get_unique_zip_codes(query_object):
    return query_object.distinct()

def get_display_fields():
    """
    Return a list of string names of the columns to aggregate
    """
    display_fields = ['number_of_persons_injured', 'number_of_persons_killed',
                'number_of_pedestrians_injured', 'number_of_pedestrians_killed',
                'number_of_cyclist_injured', 'number_of_cyclist_killed',
                'number_of_motorist_injured', 'number_of_motorist_killed']
    return display_fields

#########
#Jsonify Functions
#########
class SQLJSON (json.JSONEncoder):
    """
    Extends the built-in Python JSON encoder to handle
    decimal.Decimal values, which SQL natively returns
    #To-do: convert to float or int depending on original value.
    """
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            #Probably need to do some kind of testing,
            #lest this cast mess something up;
            #though if this is coming from a decimal in SQL, it would seem okay cast it here
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
    Returns a list of JSONs of lat/lng for plotting on agoogle maps
    request.args should contain: lat1, lng1, lat2, lng2
    and also a query term zip boolean
    """
    print(request.args)
    coords = request.args

    nullZipFlag = request.args['zip']

    query = session.query(Crash.unique_key, Crash.latitude, Crash.longitude)
    query = query.filter(Crash.latitude > float(coords['lat1'])).filter(Crash.latitude < float(coords['lat2']))
    query = query.filter(Crash.longitude > float(coords['lng1'])).filter(Crash.latitude > float(coords['lng2']))

    # if the zipcode flag was set to True
    # include only crashes without a zip code
    if nullZipFlag == 'True':
        query = query.filter(Crash.zip_code < 1)

    results_list = [as_dict(result) for result in query.all()]
    return json.dumps(results_list, cls = SQLJSON)

# marker_attributes = ["id", "name", "address", "lat", "lng", "type"]
@app.route("/years")
def get_years(query_object = None):
    """
    Returns an ordered list of years (as JSONs {"year": 2017})
    """
    if not query_object:
        year_query = session.query(func.year(Crash.date)).distinct().all() # Need to add order by year.
        return json.dumps([{'year': i[0]} for i in year_query])
    else:
        return query_object.query(func.year(Crash.date)).distinct().all() # Need to rethink this.

@app.route("/getcrash")
def crash_id():
    """
    Returns relevant crash details of a particular crash
    """

@app.route("/api/filter_request")
def queryDatabase():
    """
    Handles requests for crash numbers and can take three query terms:
        borough: a string in all caps, e.g., "BRONX"
        zip_code: a five digit zip, e.g., 10469
        year: a four digit year, e.g., 2016
    Is there anyway to keep the query in memory, so that an entirely new query doesn't have to happen each time?
    This would seem to have rely on a cookie since RESFful apps are stateless?
    Look into cached query extension.
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

    # Debugging logging
    print(request.args)
    print(sum_bundle)
    print(query.first())

    results_list = [as_dict(result) for result in query.all()]
    return json.dumps(results_list, cls = SQLJSON)

def parse_HTML_query(query_dictionary):
    """
    query_dictionary: a dictionary, usually provided by flask's request.args; values are strings.
    returns the dictionary cleared of keys with an empty value, and
    Raises ValueError if anything goes wrong
    Need to add error checking for the values and for SQLinjections
        * check for valid types and lengths
        * add a zero for zip_codes
    """
    cleaned_dictionary = {}
    allowed_keys = ('zip_code', 'borough', 'year')

    for key, value in query_dictionary.items():
        assert key in allowed_keys
        try:
            if value != '':
                cleaned_dictionary[key] = value
        except (AssertionError, ValueError):
            raise ValueError
    return cleaned_dictionary

def generate_column_bundle(field_list, schema, bundle_name, SQL_function = None):
    """
    field_list: a simple list of strings containing of the names of columns
    schema: the schema class
    SQL_function: an aggregating function object from SQLAlchemy 'func' library.
    Returns a SQLAlchemy Bundle object for ease of passing to SQLAlchemy queries

    Adds a lable element if a SQL_function has been passed in.
    """
    try:
        instrumentalized_field_list = [getattr(schema, field) for field in field_list]
    except AttributeError:
        print("Failed to generate a instrumentalized field list. Perhaps a\
        field is not in the class schema definition") #Need to figure out what to do with the error

    if SQL_function is None:
        return Bundle(bundle_name, *instrumentalized_field_list)
    else:
        #This adds a label to the function as well for clarity and making it easier ot JSONify.
        function_list = [SQL_function(field).label(SQL_function().name + '_' + field.name)
                        for field in instrumentalized_field_list]
        return Bundle(bundle_name, *function_list)

@app.route("/date_range")
def get_date_range():
    """
    Returns the min and max of dataset in a tuple of datetime.date objects
    """
    session.query(func.min(Crash.date), func.max(Crash.date))[0]
    return

def convert_to_POSIX_time(datetime_object):
    """"
    returns a float correpsonding to POSIX time
    converts a dateime.date object to a datetime.datetime object
    """
    datetime_object = datetime.combine(datetime_object, datetime.min.time())
    return datetime.timestamp(datetime_object)

def generate_date_range(beginning_date, ending_date):
    """
    Takes in two strings as datesi self
    Returns
    """
    pass

def JSONify_data (query_object, field_list):
    """
    Returns a list of JSONs in string format for passing along to browser.
    """
    #Consider replacing this function with a list comprehension.
    #[{'borough': item[0], 'victims': {display_fields2[i]._label: item[1][i]}} for item in result for i in range(8)]
    list = []
    for item in query_object:
        dictionary = {}#This doesn't gaurenteee order.  So probably need to in ordered dictionary?
        dictionary['borough'] = item[0]
        dictionary['data'] = {}
        for i in range(8):
            dictionary['data'][display_fields2[i]._label] = item[1][i]
        list.append(dictionary)

    #try also flask.jsonify(sql return object)
    display_fields3 = [func.sum(Crash.number_of_persons_injured), func.sum(Crash.number_of_persons_killed),
    func.sum(Crash.number_of_pedestrians_injured), func.sum(Crash.number_of_pedestrians_killed),
    func.sum(Crash.number_of_cyclist_injured), func.sum(Crash.number_of_cyclist_killed),
    func.sum(Crash.number_of_motorist_injured), func.sum(Crash.number_of_motorist_killed)]

    #Handles when only 'borough' has been selected, but not zip_code
    if not query_search_items[zip_code]:
        query_grouped_by_borough = session.group_by(query_search_items['borough'])
        query_grouped_by_borough()
    else:
        pass

def num_by_zip():
    borough_name = request.args['borough']
    zip_codes = session.query(Crash.zip_code, func.count())\
        .filter(Crash.borough == borough_name).group_by(Crash.zip_code).all()
    zip_codes = [{'zip': i[0], 'count': i[1]} for i in zip_codes]
    return json.dumps(zip_codes)

def filter_by_year(query_object, year):
    pass

@app.route("/api/bx_numbers")
def main_function():
    return serialize(columns, get_crashes_by_borough('BRONX'))

def serialize(columns, query_object):
    serialized_data = []
    for entry in query_object:
        entry_dict = {}
        for key in columns:
            entry_dict[key] = getattr(entry, key)
        serialized_data.append(entry_dict)
    return serialized_data

######Boilerplate EOF material###########
session = start_db_session(DATABASE_FILE)
# if __name__ == "__main__":
#     app.run(port = 8000, debug = True)
