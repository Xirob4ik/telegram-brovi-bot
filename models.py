from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_subscribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    appointments = relationship("Appointment", back_populates="user")

class Service(Base):
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    duration = Column(Integer, default=60)  # in minutes
    is_active = Column(Boolean, default=True)
    
    slots = relationship("Slot", back_populates="service")

class Slot(Base):
    __tablename__ = 'slots'
    
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_available = Column(Boolean, default=True)
    is_booked = Column(Boolean, default=False)
    
    service = relationship("Service", back_populates="slots")
    appointment = relationship("Appointment", back_populates="slot", uselist=False)

class Appointment(Base):
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    slot_id = Column(Integer, ForeignKey('slots.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    status = Column(String, default='confirmed')  # confirmed, cancelled, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="appointments")
    slot = relationship("Slot", back_populates="appointment")
    service = relationship("Service")

# Database setup
engine = create_engine(f'sqlite:///{config.DB_PATH}', echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Create default session to add initial data if needed
    session = SessionLocal()
    try:
        # Check if services exist
        if session.query(Service).count() == 0:
            default_services = [
                Service(name="Стрижка", description="Мужская стрижка", price=500.0, duration=30),
                Service(name="Борода", description="Оформление бороды", price=300.0, duration=20),
                Service(name="Комплекс", description="Стрижка + Борода", price=700.0, duration=50),
            ]
            session.add_all(default_services)
            session.commit()
            print("Default services added successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error adding default services: {e}")
    finally:
        session.close()

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass
