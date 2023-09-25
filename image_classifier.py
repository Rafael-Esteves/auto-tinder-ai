from os import listdir, rename, path, unlink
from os.path import isfile, join
import tkinter as tk
from PIL import ImageTk, Image
from auto_tinder import tinderAPI

token = "3919b0c7-7a84-4d91-8780-032dde8d0b6a"
api = tinderAPI(token)

IMAGE_FOLDER = "./images/current/"

images = iter(listdir(IMAGE_FOLDER))

persons = iter(api.nearby_persons())
current_image = None
current_person = None


def next_img():
    global current_image, images, current_person
    if (listdir(IMAGE_FOLDER)):
        try:
            current_image = next(images)
        except StopIteration:
            images = iter([f for f in listdir(IMAGE_FOLDER)
                           if isfile(join(IMAGE_FOLDER, f))])
            current_image = next(images)

        pil_img = Image.open(IMAGE_FOLDER + current_image)
        width, height = pil_img.size
        max_height = 1000
        if height > max_height:
            resize_factor = max_height / height
            pil_img = pil_img.resize(
                (int(width*resize_factor), int(height*resize_factor)),  resample=Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(pil_img)
        img_label.img = img_tk
        img_label.config(image=img_label.img)


def next_person():
    global current_person, persons, images
    delete_images()
    try:
        current_person = next(persons)
    except StopIteration:
        persons = iter(api.nearby_persons())
        current_person = next(persons)

    print("positive:" + str(len(listdir("./images/classified/positive"))))
    print("negative:" + str(len(listdir("./images/classified/negative"))))
    print(current_person)
    current_person.download_images(
        folder=IMAGE_FOLDER)
    images = iter(listdir(IMAGE_FOLDER))

    next_img()


def positive(arg):
    global current_person
    print("Positive")
    current_person.like()
    for f in listdir(IMAGE_FOLDER):
        src_path = path.join(IMAGE_FOLDER, f)
        dst_path = path.join("./images/classified/positive", f)
        rename(src_path, dst_path)

    next_person()


def negative(arg):
    global current_person
    print("Negative")
    current_person.dislike()
    for f in listdir(IMAGE_FOLDER):
        src_path = path.join(IMAGE_FOLDER, f)
        dst_path = path.join("./images/classified/negative", f)
        rename(src_path, dst_path)
    next_person()


def next_image(arg):
    print("got to next image")
    next_img()


def skip(arg):
    print("Skip")
    next_person()


def delete_images():
    for f in listdir(IMAGE_FOLDER):
        unlink(path.join(IMAGE_FOLDER, f))


if __name__ == "__main__":

    root = tk.Tk()

    img_label = tk.Label(root)
    img_label.pack()
    img_label.focus_force()
    img_label.bind("<Return>", positive)
    img_label.bind("<Delete>", negative)
    img_label.bind("<Right>", next_image)
    img_label.bind("<space>", skip)

    next_person()  # load first person

    def on_closing():
        print("closing")
        delete_images()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()
