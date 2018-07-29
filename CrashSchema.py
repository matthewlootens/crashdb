from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import column_property
from sqlalchemy import func

from sqlalchemy import Column, Integer, String, Enum, Float, DateTime, Text, Time, Date

Base = declarative_base()#Returns a base class that is inhereted by the the Crash class

class Crash(Base):
    """
    Defines the ORM interface to SQLAlchemy
    """
    __tablename__ = 'crash'

    unique_key = Column(Integer, primary_key = True)
    borough = Column(Text)
    zip_code = Column(Integer)
    latitude  = Column(Float) #40.6774
    longitude = Column(Float) #-73.8869
    location = Column(Text) #(40.677357, -73.88687)
    on_street_name = Column(Text)
    cross_street_name = Column(Text)
    off_street_name = Column(Text)
    number_of_persons_injured = Column(Integer)
    number_of_persons_killed = Column(Integer)
    number_of_pedestrians_injured = Column(Integer)
    number_of_pedestrians_killed = Column(Integer)
    number_of_cyclist_injured = Column(Integer)
    number_of_cyclist_killed = Column(Integer)
    number_of_motorist_injured = Column(Integer)
    number_of_motorist_killed  = Column(Integer)
    contributing_factor_vehicle_1 = Column(Text)#Should these be the Enum class?
    contributing_factor_vehicle_2 = Column(Text)
    contributing_factor_vehicle_3 = Column(Text)
    contributing_factor_vehicle_4 = Column(Text)
    contributing_factor_vehicle_5 = Column(Text)
    vehicle_type_code_1 = Column(Text)#Should these be the Enum class?
    vehicle_type_code_2 = Column(Text)
    vehicle_type_code_3 = Column(Text)
    vehicle_type_code_4 = Column(Text)
    vehicle_type_code_5 = Column(Text)
    #timestamp = Column(DateTime)
    time = Column(Time)
    date = Column(Date)
    year = column_property(func.year(date))
    # def as_dict(self):
    #    return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return 'Crash(%s %s)' % (self.unique_key, self.borough)
