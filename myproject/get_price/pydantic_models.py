from pydantic import BaseModel

class Price(BaseModel):
    basic: int
    product: int

class Size(BaseModel):
    price: Price

class Item(BaseModel):
    id: int
    name: str
    sizes: list[Size]

class Items(BaseModel):
    products: list[Item]
