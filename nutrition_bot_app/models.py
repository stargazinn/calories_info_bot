from django.db import models

class FoodQuery(models.Model):
    user_id = models.CharField(max_length=255)
    query = models.CharField(max_length=255)
    calories = models.FloatField()

    def __str__(self):
        return f"{self.query} ({self.calories} cal)"
