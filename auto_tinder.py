import requests
import datetime
from geopy.geocoders import Nominatim
from time import sleep
from random import random
from likeliness_classifier import Classifier
import person_detector
import tensorflow.compat.v1 as tf
from time import time
import os
import asyncio


TINDER_URL = "https://api.gotinder.com"
geolocator = Nominatim(user_agent="auto-tinder")
PROF_FILE = "./images/unclassified/profiles.txt"
SKIPPED_FILE = "./auto_skipped.txt"


class tinderAPI():

    def __init__(self, token):
        self._token = token

    def profile(self):
        data = requests.get(TINDER_URL + "/v2/profile?include=account%2Cuser",
                            headers={"X-Auth-Token": self._token}).json()
        return Profile(data["data"], self)

    def matches(self, limit=10):
        data = requests.get(
            TINDER_URL + f"/v2/matches?count={limit}", headers={"X-Auth-Token": self._token}).json()
        return list(map(lambda match: Person(match["person"], self), data["data"]["matches"]))

    def like(self, user_id):
        data = requests.get(
            TINDER_URL + f"/like/{user_id}?locale=pt", headers={"X-Auth-Token": self._token}).json()
        return {
            "is_match": data["match"],
            "liked_remaining": data["likes_remaining"],
            "status": data["status"]
        }

    def dislike(self, user_id):
        requests.get(
            TINDER_URL + f"/pass/{user_id}", headers={"X-Auth-Token": self._token}).json()
        return True

    def nearby_persons(self):
        data = requests.get(TINDER_URL + "/v2/recs/core",
                            headers={"X-Auth-Token": self._token}).json()
        return list(map(lambda user: Person(user["user"], self), data["data"]["results"]))


class Person(object):

    def __init__(self, data, api):
        self._api = api

        self.id = data["_id"]
        self.name = data.get("name", "Unknown")

        self.bio = data.get("bio", "")
        self.distance = data.get("distance_mi", 0) / 1.60934

        self.birth_date = datetime.datetime.strptime(data["birth_date"], '%Y-%m-%dT%H:%M:%S.%fZ') if data.get(
            "birth_date", False) else None

        self.gender = ["Male", "Female", "Unknown"][data.get("gender", 2)]

        self.images = list(
            map(lambda photo: photo["url"], data.get("photos", [])))

        self.jobs = list(
            map(lambda job: {"title": job.get("title", {}).get("name"), "company": job.get("company", {}).get("name")}, data.get("jobs", [])))
        self.schools = list(
            map(lambda school: school["name"], data.get("schools", [])))

        # self.interests = list(
        #     map(lambda interest: interest["name"], data.get("interests", [])["selected_interests", []]))

        if data.get("pos", False):
            self.location = geolocator.reverse(
                f'{data["pos"]["lat"]}, {data["pos"]["lon"]}')

    def __repr__(self):
        return f"{self.id}  -  {self.name} "

    def like(self):
        return self._api.like(self.id)

    def dislike(self):
        return self._api.dislike(self.id)

    def download_images(self, folder="."):
        directory = os.listdir(folder)
        if self.id in ' '.join(directory):
            print('Already captured, skipping...')
            return
        with open(PROF_FILE, "a") as f:
            f.write(self.id+"\r\n")
        index = -1
        for image_url in self.images:
            index += 1
            req = requests.get(image_url, stream=True)
            if req.status_code == 200:
                with open(f"{folder}/{self.id}_{self.name}_{index}.jpeg", "wb") as f:
                    f.write(req.content)

        print('------------------------------')
        print('Id: ', self.id)
        print('Name: ', self.name)
        print('Photo count: ', len(self.images))
        print('Total photos downloaded: ', len(directory))
        print('------------------------------')

    def predict_likeliness(self, classifier, sess):
        ratings = []

        for image in self.images:
            req = requests.get(image, stream=True)
            tmp_filename = f"./images/tmp/run.jpg"
            if req.status_code == 200:
                with open(tmp_filename, "wb") as f:
                    f.write(req.content)
            img = person_detector.get_person(tmp_filename, sess)
            if img:
                img = img.convert('L')
                img.save(tmp_filename, "jpeg")
                certainty = classifier.classify(tmp_filename)
                pos = certainty["positive"]
                ratings.append(pos)
        ratings.sort(reverse=True)
        ratings = ratings[:5]
        if len(ratings) == 0:
            return 0.001
        return ratings[0]*0.6 + sum(ratings[1:])/len(ratings[1:])*0.4


class Profile(Person):

    def __init__(self, data, api):

        super().__init__(data["user"], api)

        self.email = data["account"].get("email")
        self.phone_number = data["account"].get("account_phone_number")

        self.age_min = data["user"]["age_filter_min"]
        self.age_max = data["user"]["age_filter_max"]

        self.max_distance = data["user"]["distance_filter"]
        self.gender_filter = ["Male", "Female"][data["user"]["gender_filter"]]


if __name__ == "__main__":
    token = "d09cfe49-14fb-4c93-987c-0ec3f1ce9a8c"
    api = tinderAPI(token)

    detection_graph = person_detector.open_graph()
    with detection_graph.as_default():
        with tf.Session() as sess:

            classifier = Classifier(graph="./tf/training_output/retrained_graph.pb",
                                    labels="./tf/training_output/retrained_labels.txt")

            end_time = time() + 60*60*2.8
            while time() < end_time:
                # while True:
                try:
                    print(
                        f"------ TIME LEFT: {(end_time - time())/60}    min -----")
                    persons = api.nearby_persons()

                    for person in persons:
                        # with open(SKIPPED_FILE, "r") as f:
                        #     lines = f.readlines()
                        #     if person.id + "\n" in lines:
                        #         continue

                        score = person.predict_likeliness(classifier,   sess)

                        print("-------------------------")
                        print("Images: ", person.images)
                        print("ID: ", person.id)
                        print("Name: ", person.name)
                        print("Score: ", score)
                        print("-------------------------")

                        if score > 0.5:
                            res = person.like()
                            print("LIKE")
                            print("Response: ", res)
                        else:
                            res = person.dislike()
                            print("DISLIKE")
                            print("Response: ", res)
                        # else:
                        #     # when skipping, write id to auto_skipped.txt and check that file at the beggining of the loop to make sure we're not wasting precious processing power on the same jarro twice
                        #     with open(SKIPPED_FILE, "a") as f:
                        #         f.write(person.id+"\r\n")
                        #     print('Skipping...')
                        #     sleep(5)

                except Exception:
                    print('there was an error')

    classifier.close()
