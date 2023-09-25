from time import sleep
from random import random
from auto_tinder import tinderAPI

if __name__ == "__main__":
    token = "26339053-3c50-4999-a5c5-daadbe874bf3"
    api = tinderAPI(token)

    while True:
        persons = api.nearby_persons()
        for person in persons:
            person.download_images(
                folder="./images/classified/negative", sleep_max_for=random()*3)
