from django.db import models

class WarehouseCoefficient(models.Model):
    office_id = models.BigIntegerField(unique=True)  # warehouseID
    name = models.CharField(max_length=255)
    coefficient = models.IntegerField()
    date = models.DateTimeField()  # 🆕 новое поле
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = ("office_id", "date")


    def __str__(self):
        return f"{self.name} ({self.office_id}) → coef: {self.coefficient}, date: {self.date}"
