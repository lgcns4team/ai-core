"""
데이터 모델 정의
필요에 따라 데이터베이스 모델이나 도메인 모델을 추가할 수 있습니다.
현재는 스키마만으로 충분하여 비워둡니다.
"""

# 향후 SQLAlchemy 모델이나 MongoDB 모델 등을 추가할 수 있습니다.
# 예:
# from sqlalchemy import Column, Integer, String, Float, DateTime
# from sqlalchemy.ext.declarative import declarative_base
# 
# Base = declarative_base()
# 
# class FaceAnalysisRecord(Base):
#     __tablename__ = "face_analysis"
#     
#     id = Column(Integer, primary_key=True, index=True)
#     age = Column(Integer)
#     gender = Column(String)
#     timestamp = Column(DateTime)