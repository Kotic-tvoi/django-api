from pydantic import BaseModel
from typing import List, Optional


# --- Блок цен ---
class Price(BaseModel):
    basic: Optional[int] = None          # базовая цена без скидки
    product: Optional[int] = None        # текущая цена со скидкой
    # logistics: Optional[int] = None
    # return_: Optional[int] = None


# --- Размер / вариация ---
class Size(BaseModel):
    price: Optional[Price] = None
    # name: Optional[str] = None
    # origName: Optional[str] = None
    # rank: Optional[int] = None
    # optionId: Optional[int] = None
    # wh: Optional[int] = None
    # time1: Optional[int] = None
    # time2: Optional[int] = None
    # dtype: Optional[int] = None
    # saleConditions: Optional[int] = None
    # payload: Optional[str] = None


# --- Товар ---
class Product(BaseModel):
    id: int
    name: str
    sizes: Optional[List[Size]] = None
    # brand: Optional[str] = None
    # supplier: Optional[str] = None
    # supplierId: Optional[int] = None
    # supplierRating: Optional[float] = None
    # pics: Optional[int] = None
    # rating: Optional[float] = None
    # nmFeedbacks: Optional[int] = None
    # reviewRating: Optional[float] = None
    # nmReviewRating: Optional[float] = None
    # totalQuantity: Optional[int] = None
    # subjectId: Optional[int] = None
    # subjectParentId: Optional[int] = None
    # kindId: Optional[int] = None
    # volume: Optional[int] = None
    # weight: Optional[float] = None


# --- Корневая модель (главное изменение) ---
class Items(BaseModel):
    products: List[Product] = []
