from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import CrashSchema

#from sqlalchemy.ext.declarative import declarative_base
#from sqlalchemy import Column, Integer, String, Enum, Float, DateTime, Text

class CrashDatabase():
    """
    A class that represents a connection to a mySQL database using sqlalchemy
    library
    """
    def __init__(self, database_name, sql_flavor = 'sqlite', echo_setting = True):
        """
        New instances of CrashDatabase
        """
        self.engine = create_engine('%s://%s' % (sql_flavor,
            database_name), echo = echo_setting)
        self.set_metadata(self.engine)
        self.Session = sessionmaker(bind = self.engine)
        #Returns a Class, here called Session, which is a factory
        #for new Session objects. Creates a new Session object
        #whenever a connection to the database is needed.

    def set_metadata(self, engine):
        CrashSchema.Base.metadata.create_all(engine)

    def new_session(self):
        return self.Session()

    def commit(self):
        self.session.commit()

####
####Temporary Testing Code
####
# a = CrashDatabase()
# session = a.new_session()
#
# bx_crashes = session.query(Crash).filter_by(borough = "BRONX")
# engine = create_engine('sqlite:///crash12.db', echo = True)
#
# Session = sessionmaker(bind = engine)
# session = Session()
#
# crash_rows = [Crash(**row) for index, row in reduced_data.to_dict(orient='index').items()]
# session.add_all(crash_rows)
# session.commit()
