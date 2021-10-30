from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

import os

Base = declarative_base()
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = 'sqlite:///' + os.path.join(basedir, './.votes.db')
engine = create_engine(db_path, echo=False)


class Polls(Base):
    __tablename__ = 'polls'
    id = Column(Integer, primary_key=True)
    pid = Column(String)
    text = Column(String)
    yes_count = Column(Integer)
    no_count = Column(Integer)


class Voters(Base):
    __tablename__ = 'voters'
    id = Column(Integer, primary_key=True)  # doesn't used
    poll_id = Column(Integer)
    variant = Column(String)
    user_id = Column(Integer)


class Variants(Base):
    __tablename__ = 'variants'
    poll_id = Column(Integer)
    variant_callback = Column(String, primary_key=True)
    yes_no = Column(String(3))
