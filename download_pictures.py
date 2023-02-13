from time import sleep
from random import random
from auto_tinder import tinderAPI

if __name__ == "__main__":
    token = "YOUR_API_KEY"
    api = tinderAPI(token)

    while True:
        persons = api.nearby_persons()
        for person in persons:
            person.download_images(folder="./images/unclassified", sleep_max_for=random()*3)
            print(person.name)
            print(person.bio)
            sleep(random()*10)
        sleep(random()*10)

