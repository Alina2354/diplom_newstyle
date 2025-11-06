from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime


class UserRead(BaseModel):
    
    id: int              
    email: EmailStr      
    is_active: bool      
    is_superuser: bool   
    is_verified: bool    
    created_at: datetime 
    model_config = ConfigDict(from_attributes=True)
    
class UserCreate(BaseModel):

    email: EmailStr      
    password: str        
    

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None       
    password: Optional[str] = None          
    is_active: Optional[bool] = None        
    is_superuser: Optional[bool] = None    
    is_verified: Optional[bool] = None     


class UserLogin(BaseModel):
    email: EmailStr     
    password: str       
