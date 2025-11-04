from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

class Participant(Base):
    __tablename__ = 'participants'
    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    display_name = Column(String(200))
    roles = Column(JSON, default=list)

class Publication(Base):
    __tablename__ = 'publications'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    pub_metadata = Column('metadata', JSON)
    owner_id = Column(Integer, ForeignKey('participants.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship('Participant')

class Request(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)
    subject = Column(String(255))
    body = Column(Text)
    publication_id = Column(Integer, ForeignKey('publications.id'))
    requester_id = Column(Integer, ForeignKey('participants.id'))
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    publication = relationship('Publication')
    requester = relationship('Participant')

class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('requests.id'))
    terms = Column(JSON)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    request = relationship('Request')

class Transfer(Base):
    __tablename__ = 'transfers'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    object_path = Column(String(1024))
    presigned_url = Column(Text)
    status = Column(String(50), default='initiated')
    created_at = Column(DateTime, default=datetime.utcnow)
    contract = relationship('Contract')

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    actor = Column(String(255))
    action = Column(String(255))
    resource_type = Column(String(100))
    resource_id = Column(String(100))
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)